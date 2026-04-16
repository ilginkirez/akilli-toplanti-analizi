import asyncio
import datetime
import json
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..services import livekit_service
from ..services.speech_analysis_service import speech_analysis_service
from ..services.session_store import session_store

router = APIRouter()
STORAGE_DIR = session_store.sessions_dir


def _persist_session_metadata(session_id: str) -> None:
    session = session_store.load_session(session_id)
    session_dir = Path(STORAGE_DIR) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "session.json").write_text(
        json.dumps(session, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


@router.post("")
async def create_session(request_data: Dict[str, Any]):
    session_id = request_data.get("session_id") or f"ses_{uuid.uuid4().hex[:8]}"

    try:
        await livekit_service.create_room(
            session_id,
            metadata={"session_id": session_id},
            max_participants=request_data.get("max_participants"),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    session = session_store.ensure_session(session_id)
    session["status"] = "active"
    session_store.save_session(session_id, session)
    return {"session_id": session_id, "status": "active"}


@router.post("/token")
async def create_token(request_data: Dict[str, Any]):
    session_id = request_data.get("session_id")
    display_name = request_data.get("display_name", "Unknown")
    device_info = request_data.get("device_info", {})

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    participant_id = f"par_{uuid.uuid4().hex[:6]}"
    server_data = {
        "participant_id": participant_id,
        "display_name": display_name,
        "session_id": session_id,
        "device_info": device_info,
        "issued_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    session_store.register_pending_participant(
        session_id=session_id,
        participant_id=participant_id,
        display_name=display_name,
        device_info=device_info,
    )
    _persist_session_metadata(session_id)

    try:
        await livekit_service.create_room(
            room_name=session_id,
            metadata={"session_id": session_id},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"LiveKit room could not be prepared: {exc}",
        ) from exc

    try:
        token = livekit_service.create_access_token(
            room_name=session_id,
            participant_id=participant_id,
            display_name=display_name,
            metadata=server_data,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    connection_id = participant_id
    session_store.attach_connection(
        session_id=session_id,
        participant_id=participant_id,
        connection_id=connection_id,
        server_data=server_data,
        client_data={"display_name": display_name},
    )
    _persist_session_metadata(session_id)

    session_store.update_recording(
        session_id,
        {
            "mode": "Egress",
            "status": "disabled",
            "reason": "LiveKit egress bu asamada etkinlestirilmedi.",
        },
    )
    recording_state = session_store.load_session(session_id)["recording"]
    _persist_session_metadata(session_id)

    return {
        "token": token,
        "participant_id": participant_id,
        "session_id": session_id,
        "connection_id": connection_id,
        "ws_url": livekit_service.public_ws_url(),
        "provider": "livekit",
        "server_data": server_data,
        "recording_status": recording_state.get("status"),
        "recording_id": recording_state.get("recording_id"),
    }


@router.get("/{session_id}/speech-analysis")
async def get_speech_analysis(session_id: str):
    return session_store.load_session(session_id).get("speech_analysis", {})


@router.post("/{session_id}/speech-analysis")
async def build_speech_analysis(session_id: str):
    try:
        return await asyncio.to_thread(
            speech_analysis_service.analyze_session,
            session_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{session_id}")
async def get_session(session_id: str):
    return session_store.load_session(session_id)


@router.post("/{session_id}/stop")
async def stop_session(session_id: str):
    try:
        await livekit_service.delete_room(session_id)
    except Exception:
        pass

    session = session_store.load_session(session_id)
    session["status"] = "ended"
    session["finalized_at"] = datetime.datetime.now(datetime.UTC).isoformat()
    session_store.save_session(session_id, session)

    return {
        "status": session["status"],
        "session_id": session_id,
        "recording": session.get("recording", {}),
    }


@router.get("")
async def list_active_sessions():
    rooms = []
    try:
        response = await livekit_service.list_rooms()
        rooms = response.get("rooms", [])
    except Exception:
        pass

    return {"sessions": rooms}

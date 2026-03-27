import asyncio
import datetime
import json
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..services import openvidu_service
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
        await openvidu_service.create_session(session_id)
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
        await openvidu_service.create_session(session_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"OpenVidu session could not be prepared: {exc}",
        ) from exc

    try:
        token_or_connection = await openvidu_service.create_token(
            session_id,
            participant_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if isinstance(token_or_connection, str):
        connection = {"token": token_or_connection}
    else:
        connection = token_or_connection

    connection_id = connection.get("id") or connection.get("connectionId")
    session_store.attach_connection(
        session_id=session_id,
        participant_id=participant_id,
        connection_id=connection_id or f"pending_{participant_id}",
        server_data=server_data,
        client_data={"display_name": display_name},
    )
    _persist_session_metadata(session_id)

    recording_state = session_store.load_session(session_id)["recording"]
    if session_store.can_start_recording(session_id):
        try:
            recording = await openvidu_service.start_individual_recording(
                session_id=session_id,
                name=session_id,
            )
            session_store.update_recording(
                session_id,
                {
                    "status": recording.get("status", "started"),
                    "recording_id": recording.get("id"),
                    "name": recording.get("name", session_id),
                    "started_at": datetime.datetime.now(datetime.UTC).isoformat(),
                },
            )
            recording_state = session_store.load_session(session_id)["recording"]
        except Exception as exc:
            session_store.update_recording(
                session_id,
                {
                    "status": "failed",
                    "reason": str(exc),
                },
            )
            recording_state = session_store.load_session(session_id)["recording"]
        _persist_session_metadata(session_id)

    return {
        "token": connection.get("token"),
        "participant_id": participant_id,
        "session_id": session_id,
        "connection_id": connection_id,
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
    session = session_store.load_session(session_id)
    recording = session.get("recording", {})
    recording_id = recording.get("recording_id")

    if recording_id and recording.get("status") in {"started", "starting"}:
        try:
            stopped = await openvidu_service.stop_recording(recording_id)
            session_store.update_recording(
                session_id,
                {
                    "status": stopped.get("status", "stopped"),
                    "stopped_at": datetime.datetime.now(datetime.UTC).isoformat(),
                    "duration_sec": stopped.get("duration"),
                    "size_bytes": stopped.get("size"),
                    "reason": stopped.get("reason"),
                },
            )
        except Exception as exc:
            session_store.update_recording(
                session_id,
                {
                    "status": "failed",
                    "reason": str(exc),
                },
            )

    try:
        await openvidu_service.close_session(session_id)
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

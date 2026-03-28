import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..services import openvidu_service
from ..services.session_store import session_store

router = APIRouter()


@router.post("/start")
async def start_recording(data: Dict[str, Any]):
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    if not session_store.can_start_recording(session_id):
        return {
            "status": "already_started",
            "recording": session_store.load_session(session_id).get("recording", {}),
        }

    try:
        recording = await openvidu_service.start_individual_recording(
            session_id=session_id,
            name=data.get("name") or session_id,
        )
    except Exception as exc:
        session_store.update_recording(
            session_id,
            {
                "status": "failed",
                "reason": str(exc),
            },
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    session_store.update_recording(
        session_id,
        {
            "status": recording.get("status", "started"),
            "recording_id": recording.get("id"),
            "name": recording.get("name", session_id),
            "started_at": datetime.datetime.utcnow().isoformat(),
        },
    )
    return {"status": "started", "recording": session_store.load_session(session_id)["recording"]}


@router.post("/stop")
async def stop_recording(data: Dict[str, Any]):
    session_id = data.get("session_id")
    recording_id = data.get("recording_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    if not recording_id:
        recording_id = session_store.load_session(session_id).get("recording", {}).get("recording_id")
    if not recording_id:
        raise HTTPException(status_code=404, detail="recording not found")

    try:
        stopped = await openvidu_service.stop_recording(recording_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    session_store.update_recording(
        session_id,
        {
            "status": stopped.get("status", "stopped"),
            "stopped_at": datetime.datetime.utcnow().isoformat(),
            "duration_sec": stopped.get("duration"),
            "size_bytes": stopped.get("size"),
            "reason": stopped.get("reason"),
        },
    )
    return {"status": "stopped", "recording": session_store.load_session(session_id)["recording"]}


@router.get("/{session_id}")
async def list_recordings(session_id: str):
    return session_store.load_session(session_id).get("recording", {})

import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..services.session_store import session_store

router = APIRouter()


@router.post("/{session_id}/events")
async def log_event(session_id: str, request_data: Dict[str, Any]):
    session_store.ensure_session(session_id)

    event_payload = {
        "event": request_data.get("event_type", "unknown"),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "session_id": session_id,
        "participant_id": request_data.get("participant_id"),
        "connection_id": request_data.get("connection_id"),
        "stream_id": request_data.get("stream_id"),
        "metadata": request_data.get("metadata", {}),
    }

    session_store.append_event(session_id, event_payload)
    return {"status": "success"}


@router.post("/{session_id}/speaking")
async def log_speaking(session_id: str, request_data: Dict[str, Any]):
    if not session_store.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    return await log_event(
        session_id,
        {
            "event_type": "speaking_" + ("start" if request_data.get("is_speaking") else "stop"),
            "participant_id": request_data.get("participant_id"),
            "connection_id": request_data.get("connection_id"),
            "stream_id": request_data.get("stream_id"),
            "metadata": request_data.get("metadata", {}),
        },
    )

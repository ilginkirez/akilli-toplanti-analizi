import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..services.session_store import session_store

router = APIRouter()


@router.post("/start")
async def start_recording(data: Dict[str, Any]):
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    session_store.update_recording(
        session_id,
        {
            "status": "disabled",
            "name": data.get("name") or session_id,
            "reason": "LiveKit egress bu asamada etkinlestirilmedi.",
            "updated_at": datetime.datetime.utcnow().isoformat(),
        },
    )
    return {
        "status": "disabled",
        "recording": session_store.load_session(session_id)["recording"],
    }


@router.post("/stop")
async def stop_recording(data: Dict[str, Any]):
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    session_store.update_recording(
        session_id,
        {
            "status": "disabled",
            "stopped_at": datetime.datetime.utcnow().isoformat(),
            "reason": "LiveKit egress etkin degil, durdurulacak aktif kayit yok.",
        },
    )
    return {
        "status": "disabled",
        "recording": session_store.load_session(session_id)["recording"],
    }


@router.get("/{session_id}")
async def list_recordings(session_id: str):
    return session_store.load_session(session_id).get("recording", {})

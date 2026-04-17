import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..services.egress_recording_service import (
    maybe_finalize_session_recording,
    start_audio_track_egress,
    stop_participant_egress,
)
from ..services import livekit_service
from ..services.session_store import session_store

router = APIRouter()


@router.post("/register")
async def register_participant(data: Dict[str, Any]):
    session_id = data.get("session_id")
    participant_id = data.get("participant_id")
    connection_id = data.get("connection_id")

    if not session_id or not participant_id or not connection_id:
        raise HTTPException(
            status_code=400,
            detail="session_id, participant_id and connection_id are required",
        )

    session_store.attach_connection(
        session_id=session_id,
        participant_id=participant_id,
        connection_id=connection_id,
        client_data=data.get("client_data"),
        server_data=data.get("server_data"),
        location=data.get("location"),
        ip=data.get("ip"),
        platform=data.get("platform"),
        connected_at=data.get("connected_at")
        or datetime.datetime.now(datetime.UTC).isoformat(),
    )

    return {"status": "registered", "participant_id": participant_id}


@router.patch("/{participant_id}/leave")
async def leave_participant(participant_id: str, data: Dict[str, Any]):
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    await stop_participant_egress(
        session_id=session_id,
        participant_id=participant_id,
        reason=data.get("reason") or "client_leave",
        ended_at=data.get("left_at"),
        run_analysis=False,
    )
    session_store.mark_participant_left(
        session_id=session_id,
        participant_id=participant_id,
        connection_id=data.get("connection_id"),
        left_at=data.get("left_at") or datetime.datetime.now(datetime.UTC).isoformat(),
        reason=data.get("reason"),
    )
    await maybe_finalize_session_recording(session_id)

    return {"status": "left", "participant_id": participant_id}


@router.patch("/{participant_id}/stream")
async def update_stream(participant_id: str, data: Dict[str, Any]):
    session_id = data.get("session_id")
    connection_id = data.get("connection_id")
    stream_id = data.get("stream_id")

    if not session_id or not connection_id or not stream_id:
        raise HTTPException(
            status_code=400,
            detail="session_id, connection_id and stream_id are required",
        )

    session_store.attach_connection(
        session_id=session_id,
        participant_id=participant_id,
        connection_id=connection_id,
        client_data=data.get("client_data"),
        server_data=data.get("server_data"),
    )
    session_store.attach_stream(
        session_id=session_id,
        connection_id=connection_id,
        stream_id=stream_id,
        audio_enabled=data.get("has_audio"),
        video_enabled=data.get("has_video"),
        video_source=data.get("video_source"),
        media_type=data.get("media_type"),
    )

    audio_track_id = data.get("audio_track_id")
    if audio_track_id:
        await start_audio_track_egress(
            session_id=session_id,
            participant_id=participant_id,
            track_id=audio_track_id,
            connection_id=connection_id,
        )

    return {"status": "stream_updated", "participant_id": participant_id}


@router.delete("/{participant_id}")
async def remove_participant(participant_id: str, data: Dict[str, Any]):
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    await stop_participant_egress(
        session_id=session_id,
        participant_id=participant_id,
        reason=data.get("reason") or "removed_by_admin",
        ended_at=data.get("left_at"),
        run_analysis=False,
    )
    try:
        await livekit_service.remove_participant(session_id, participant_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    session_store.mark_participant_left(
        session_id=session_id,
        participant_id=participant_id,
        left_at=data.get("left_at") or datetime.datetime.now(datetime.UTC).isoformat(),
        reason=data.get("reason") or "removed_by_admin",
    )
    await maybe_finalize_session_recording(session_id)

    return {"status": "removed", "participant_id": participant_id}

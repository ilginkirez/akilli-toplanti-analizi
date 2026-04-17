import json
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Request

from ..services import livekit_service
from ..services.egress_recording_service import (
    maybe_finalize_session_recording,
    start_audio_track_egress,
    stop_participant_egress,
    stop_session_egresses,
)
from ..services.meeting_store import meeting_store
from ..services.session_store import _jsonify, _utc_now_iso, session_store

router = APIRouter()


def _parse_metadata(value: str | None) -> Dict[str, Any]:
    parsed = _jsonify(value or "")
    if isinstance(parsed, dict):
        return parsed
    return {"raw": value or ""}


def _track_kind(track_payload: Dict[str, Any]) -> str:
    track_type = str(track_payload.get("type") or "").strip().lower()
    source = str(track_payload.get("source") or "").strip().lower()
    mime_type = str(track_payload.get("mimeType") or "").strip().lower()

    if track_type in {"audio", "video"}:
        return track_type
    if mime_type.startswith("audio/"):
        return "audio"
    if mime_type.startswith("video/"):
        return "video"
    if source == "microphone":
        return "audio"
    if source in {"camera", "screen_share", "screen_share_audio", "screen_share_video"}:
        return "video"
    return ""


@router.get("/rooms")
async def get_rooms():
    try:
        response = await livekit_service.list_rooms()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"rooms": response.get("rooms", [])}


@router.post("/rooms")
async def create_room(payload: Dict[str, Any]):
    room_name = payload.get("room_name") or payload.get("session_id")
    if not room_name:
        raise HTTPException(status_code=400, detail="room_name or session_id required")

    try:
        room = await livekit_service.create_room(
            room_name=room_name,
            metadata={
                "created_by": payload.get("created_by"),
                "description": payload.get("description"),
            },
            max_participants=payload.get("max_participants"),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"status": "ok", "room": room}


@router.delete("/rooms/{room_name}")
async def delete_room(room_name: str):
    try:
        result = await livekit_service.delete_room(room_name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"status": "deleted", "room_name": room_name, "result": result}


@router.get("/rooms/{room_name}/participants")
async def get_room_participants(room_name: str):
    try:
        response = await livekit_service.list_participants(room_name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"participants": response.get("participants", [])}


@router.post("/webhook")
async def livekit_webhook(
    request: Request,
    authorization: str | None = Header(default=None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    raw_body = (await request.body()).decode("utf-8")

    try:
        event = livekit_service.build_webhook_receiver().receive(raw_body, authorization)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Webhook verification failed: {exc}") from exc

    room_name = event.room.name if event.room and event.room.name else None
    event_name = event.event

    if not room_name or not event_name:
        return {"status": "ignored"}

    session_store.ensure_session(room_name)
    payload = json.loads(raw_body)
    session_store.append_event(room_name, payload)
    session_store.update_webhook_meta(room_name, None)

    participant = event.participant
    track = event.track
    track_payload = payload.get("track", {}) if isinstance(payload.get("track"), dict) else {}

    if event_name == "room_started":
        session = session_store.load_session(room_name)
        session["status"] = "active"
        session_store.save_session(room_name, session)

    elif event_name == "participant_joined" and participant:
        metadata = _parse_metadata(participant.metadata)
        session_store.attach_connection(
            session_id=room_name,
            participant_id=participant.identity,
            connection_id=participant.sid,
            client_data={"display_name": participant.name},
            server_data=metadata,
            connected_at=_utc_now_iso(),
        )

    elif event_name in {"participant_left", "participant_connection_aborted"} and participant:
        await stop_participant_egress(
            session_id=room_name,
            participant_id=participant.identity,
            reason=event_name,
            run_analysis=False,
        )
        session_store.mark_participant_left(
            session_id=room_name,
            participant_id=participant.identity,
            connection_id=participant.sid,
            left_at=_utc_now_iso(),
            reason=event_name,
        )

    elif event_name == "track_published" and participant and track:
        track_type = _track_kind(track_payload)
        source = str(track_payload.get("source", "")).lower()
        session_store.attach_stream(
            session_id=room_name,
            connection_id=participant.sid,
            stream_id=track_payload.get("sid") or track.sid,
            audio_enabled=track_type == "audio",
            video_enabled=track_type == "video",
            video_source=source,
            media_type=track_type or "audio_video",
        )
        if track_type == "audio" and source in {"", "microphone"}:
            await start_audio_track_egress(
                session_id=room_name,
                participant_id=participant.identity,
                track_id=track_payload.get("sid") or track.sid,
                connection_id=participant.sid,
            )

    elif event_name == "track_unpublished" and participant and track:
        track_type = _track_kind(track_payload)
        source = str(track_payload.get("source", "")).lower()
        if track_type == "audio" and source in {"", "microphone"}:
            await stop_participant_egress(
                session_id=room_name,
                participant_id=participant.identity,
                reason="track_unpublished",
                run_analysis=False,
            )

    elif event_name == "room_finished":
        await stop_session_egresses(room_name, reason="room_finished")
        session = session_store.load_session(room_name)
        session["status"] = "ended"
        session["finalized_at"] = _utc_now_iso()
        session_store.save_session(room_name, session)
        if session.get("meeting_id"):
            meeting_store.update_status(session["meeting_id"], "completed")
        await maybe_finalize_session_recording(room_name)

    return {"status": "ok"}

import asyncio
from typing import Any, Dict

from fastapi import APIRouter

from ..services import openvidu_service
from ..services.speech_analysis_service import speech_analysis_service
from ..services.session_store import _from_timestamp_ms, _jsonify, session_store

router = APIRouter()


def _parse_payload_data(value: Any) -> Dict[str, Any]:
    parsed = _jsonify(value)
    if isinstance(parsed, dict):
        return parsed
    return {"raw": value}


@router.post("/webhook")
async def openvidu_webhook(payload: Dict[str, Any]):
    event_type = payload.get("event")
    session_id = payload.get("sessionId")
    timestamp_ms = payload.get("timestamp")

    if not event_type or not session_id:
        return {"status": "ignored"}

    session_store.ensure_session(session_id)
    session_store.update_webhook_meta(session_id, timestamp_ms)
    session_store.append_event(session_id, payload)

    if event_type == "sessionCreated":
        session = session_store.load_session(session_id)
        session["status"] = "active"
        session_store.save_session(session_id, session)

    elif event_type == "participantJoined":
        server_data = _parse_payload_data(payload.get("serverData"))
        client_data = _parse_payload_data(payload.get("clientData"))
        session_store.attach_connection(
            session_id=session_id,
            participant_id=server_data.get("participant_id"),
            connection_id=payload.get("connectionId"),
            client_data=client_data,
            server_data=server_data,
            location=payload.get("location"),
            ip=payload.get("ip"),
            platform=payload.get("platform"),
            connected_at=_from_timestamp_ms(payload.get("timestamp")),
        )

    elif event_type == "participantLeft":
        session_store.mark_participant_left(
            session_id=session_id,
            connection_id=payload.get("connectionId"),
            left_at=_from_timestamp_ms(payload.get("timestamp")),
            reason=payload.get("reason"),
        )

    elif event_type == "webrtcConnectionCreated" and payload.get("connection") == "OUTBOUND":
        session_store.attach_stream(
            session_id=session_id,
            connection_id=payload.get("connectionId"),
            stream_id=payload.get("streamId"),
            audio_enabled=payload.get("audioEnabled"),
            video_enabled=payload.get("videoEnabled"),
            video_source=payload.get("videoSource"),
            media_type="outbound",
        )

    elif event_type == "recordingStatusChanged":
        updates = {
            "recording_id": payload.get("id"),
            "name": payload.get("name"),
            "status": payload.get("status"),
            "has_audio": payload.get("hasAudio"),
            "has_video": payload.get("hasVideo"),
            "duration_sec": payload.get("duration"),
            "size_bytes": payload.get("size"),
            "reason": payload.get("reason"),
            "last_event": payload,
        }
        if payload.get("status") == "started":
            updates["started_at"] = _from_timestamp_ms(payload.get("startTime") or payload.get("timestamp"))
        if payload.get("status") == "stopped":
            updates["stopped_at"] = _from_timestamp_ms(payload.get("timestamp"))
        if payload.get("status") == "ready":
            updates["ready_at"] = _from_timestamp_ms(payload.get("timestamp"))

        session_store.update_recording(session_id, updates)

        if payload.get("status") == "ready" and payload.get("outputMode") == "INDIVIDUAL":
            try:
                await openvidu_service.get_recording(payload.get("id"))
            except Exception:
                pass
            synced_session = session_store.sync_individual_recording_archive(
                session_id=session_id,
                recording_name=payload.get("name"),
                recording_id=payload.get("id"),
            )
            if synced_session:
                try:
                    await asyncio.to_thread(
                        speech_analysis_service.analyze_session,
                        session_id,
                    )
                except Exception:
                    pass

    elif event_type == "sessionDestroyed":
        session = session_store.load_session(session_id)
        session["status"] = "ended"
        session["finalized_at"] = _from_timestamp_ms(payload.get("timestamp"))
        session["total_duration_sec"] = payload.get("duration")
        session_store.save_session(session_id, session)

    return {"status": "ok"}

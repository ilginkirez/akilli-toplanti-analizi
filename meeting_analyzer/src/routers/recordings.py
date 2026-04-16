import asyncio
import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..services.session_store import session_store
from ..services.speech_analysis_service import speech_analysis_service

router = APIRouter()


def _parse_iso(value: Optional[str]) -> Optional[datetime.datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _pick_extension(upload: UploadFile, mime_type: str) -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix in {".webm", ".wav", ".ogg", ".mp3", ".m4a"}:
        return suffix
    if "wav" in mime_type:
        return ".wav"
    if "ogg" in mime_type:
        return ".ogg"
    if "mpeg" in mime_type or "mp3" in mime_type:
        return ".mp3"
    if "mp4" in mime_type or "m4a" in mime_type:
        return ".m4a"
    return ".webm"


async def _run_analysis_if_ready(session_id: str) -> None:
    session = session_store.load_session(session_id)
    has_tracks = any(
        participant.get("recording_files")
        for participant in session.get("participants", [])
    )
    has_active_participants = any(
        participant.get("active")
        for participant in session.get("participants", [])
    )
    if not has_tracks or has_active_participants:
        return

    try:
        await asyncio.to_thread(speech_analysis_service.analyze_session, session_id)
    except Exception:
        # Analysis failures are persisted by the service itself.
        pass


@router.post("/start")
async def start_recording(data: Dict[str, Any]):
    session_id = data.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    session_store.update_recording(
        session_id,
        {
            "mode": "LOCAL_INDIVIDUAL",
            "name": data.get("name") or session_id,
            "status": "started",
            "started_at": data.get("started_at")
            or session_store.load_session(session_id)["recording"].get("started_at")
            or datetime.datetime.now(datetime.UTC).isoformat(),
            "reason": None,
            "updated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        },
    )
    return {
        "status": "started",
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
            "status": "uploaded",
            "stopped_at": data.get("stopped_at")
            or datetime.datetime.now(datetime.UTC).isoformat(),
            "reason": None,
        },
    )
    await _run_analysis_if_ready(session_id)
    return {
        "status": "uploaded",
        "recording": session_store.load_session(session_id)["recording"],
    }


@router.post("/upload/local")
async def upload_recording(
    session_id: str = Form(...),
    participant_id: str = Form(...),
    connection_id: Optional[str] = Form(None),
    stream_id: Optional[str] = Form(None),
    started_at: Optional[str] = Form(None),
    ended_at: Optional[str] = Form(None),
    mime_type: Optional[str] = Form(None),
    device_label: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    session = session_store.load_session(session_id)
    participant = next(
        (
            item
            for item in session.get("participants", [])
            if item.get("participant_id") == participant_id
        ),
        None,
    )
    if participant is None:
        raise HTTPException(status_code=404, detail="participant not found")

    started_dt = _parse_iso(started_at) or datetime.datetime.now(datetime.UTC)
    ended_dt = _parse_iso(ended_at)

    recording_started_at = session.get("recording", {}).get("started_at")
    recording_start_dt = _parse_iso(recording_started_at)
    if recording_start_dt is None or started_dt < recording_start_dt:
        recording_start_dt = started_dt
        session_store.update_recording(
            session_id,
            {
                "mode": "LOCAL_INDIVIDUAL",
                "status": "started",
                "started_at": recording_start_dt.isoformat(),
                "reason": None,
            },
        )

    effective_mime = (mime_type or file.content_type or "audio/webm").lower()
    extension = _pick_extension(file, effective_mime)
    recordings_dir = session_store.recordings_dir / session_id / "individual"
    recordings_dir.mkdir(parents=True, exist_ok=True)

    timestamp = started_dt.strftime("%Y%m%dT%H%M%S")
    safe_participant = participant_id.replace("/", "_")
    target_path = recordings_dir / f"{safe_participant}-{timestamp}{extension}"
    payload = await file.read()
    target_path.write_bytes(payload)

    start_offset_ms = max(
        0,
        int(round((started_dt - recording_start_dt).total_seconds() * 1000)),
    )
    end_offset_ms = None
    if ended_dt is not None:
        end_offset_ms = max(
            start_offset_ms,
            int(round((ended_dt - recording_start_dt).total_seconds() * 1000)),
        )

    relative_path = target_path.relative_to(session_store.recordings_dir).as_posix()
    recording_info = {
        "stream_id": stream_id or participant.get("stream_id") or participant_id,
        "connection_id": connection_id or participant.get("connection_id"),
        "file_path": relative_path,
        "has_audio": True,
        "has_video": False,
        "type_of_video": "NONE",
        "start_time_offset_ms": start_offset_ms,
        "end_time_offset_ms": end_offset_ms,
        "size": len(payload),
        "mime_type": effective_mime,
        "device_label": device_label,
        "recorded_started_at": started_dt.isoformat(),
        "recorded_ended_at": ended_dt.isoformat() if ended_dt else None,
    }
    session_store.add_participant_recording_file(
        session_id=session_id,
        participant_id=participant_id,
        recording_info=recording_info,
    )

    session_store.update_recording(
        session_id,
        {
            "mode": "LOCAL_INDIVIDUAL",
            "status": "uploaded",
            "ready_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "stopped_at": ended_dt.isoformat() if ended_dt else None,
            "reason": None,
        },
    )

    await _run_analysis_if_ready(session_id)

    return {
        "status": "uploaded",
        "session_id": session_id,
        "participant_id": participant_id,
        "file_path": relative_path,
        "start_time_offset_ms": start_offset_ms,
        "end_time_offset_ms": end_offset_ms,
    }


@router.get("/{session_id}")
async def list_recordings(session_id: str):
    return session_store.load_session(session_id).get("recording", {})

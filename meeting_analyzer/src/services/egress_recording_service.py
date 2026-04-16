import asyncio
import datetime
import mimetypes
from pathlib import PurePosixPath
from typing import Any, Dict, Optional

from . import livekit_service
from .session_store import session_store
from .speech_analysis_service import speech_analysis_service

EGRESS_RECORDINGS_ROOT = PurePosixPath("/out/recordings")


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime.datetime]:
    if not value:
        return None

    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _find_participant(session: Dict[str, Any], participant_id: str) -> Optional[Dict[str, Any]]:
    return next(
        (
            item
            for item in session.get("participants", [])
            if item.get("participant_id") == participant_id
        ),
        None,
    )


def _derive_relative_recording_path(path_like: Optional[str]) -> Optional[str]:
    if not path_like:
        return None

    path = PurePosixPath(path_like)
    try:
        return path.relative_to(EGRESS_RECORDINGS_ROOT).as_posix()
    except ValueError:
        marker = "/recordings/"
        normalized = path.as_posix()
        if marker in normalized:
            return normalized.split(marker, 1)[1].lstrip("/")
        return normalized.lstrip("/")


def _build_output_paths(session_id: str, participant_id: str, track_id: str) -> tuple[str, str]:
    relative_path = f"{session_id}/individual/{participant_id}-{track_id}.ogg"
    absolute_path = (EGRESS_RECORDINGS_ROOT / relative_path).as_posix()
    return relative_path, absolute_path


def _guess_mime_type(file_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "audio/ogg"


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
        # Analysis failures are already persisted by the service.
        pass


def _sync_recording_mode(session_id: str, started_at: Optional[str] = None) -> None:
    session = session_store.load_session(session_id)
    current_started_at = session.get("recording", {}).get("started_at")
    next_started_at = started_at or current_started_at or _utc_now_iso()

    current_started_dt = _parse_iso(current_started_at)
    next_started_dt = _parse_iso(next_started_at)
    if current_started_dt and next_started_dt and current_started_dt <= next_started_dt:
        next_started_at = current_started_at

    session_store.update_recording(
        session_id,
        {
            "mode": "LIVEKIT_TRACK_EGRESS",
            "status": "started",
            "started_at": next_started_at,
            "reason": None,
        },
    )


async def start_audio_track_egress(
    session_id: str,
    participant_id: str,
    track_id: str,
    *,
    connection_id: Optional[str] = None,
    started_at: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    session = session_store.load_session(session_id)
    participant = _find_participant(session, participant_id)
    if participant is None:
        return None

    active_egress = participant.get("audio_egress") or {}
    if (
        active_egress.get("status") in {"starting", "active"}
        and active_egress.get("track_id") == track_id
    ):
        return active_egress

    if active_egress.get("status") in {"starting", "active"} and active_egress.get("egress_id"):
        await stop_participant_egress(
            session_id,
            participant_id,
            reason="track_republished",
            ended_at=started_at,
            run_analysis=False,
        )
        session = session_store.load_session(session_id)
        participant = _find_participant(session, participant_id)
        if participant is None:
            return None

    _sync_recording_mode(session_id, started_at=started_at)

    relative_path, absolute_path = _build_output_paths(session_id, participant_id, track_id)
    info = await livekit_service.start_track_egress(
        room_name=session_id,
        track_id=track_id,
        filepath=absolute_path,
    )

    session = session_store.load_session(session_id)
    participant = _find_participant(session, participant_id)
    if participant is None:
        return None

    participant["audio_egress"] = {
        "egress_id": info.get("egress_id"),
        "track_id": track_id,
        "connection_id": connection_id or participant.get("connection_id"),
        "relative_path": relative_path,
        "started_at": started_at or _utc_now_iso(),
        "status": "active",
    }
    session_store.save_session(session_id, session)
    return participant["audio_egress"]


async def stop_participant_egress(
    session_id: str,
    participant_id: str,
    *,
    reason: str,
    ended_at: Optional[str] = None,
    run_analysis: bool = True,
) -> Optional[Dict[str, Any]]:
    session = session_store.load_session(session_id)
    participant = _find_participant(session, participant_id)
    if participant is None:
        return None

    egress_state = participant.get("audio_egress")
    if not isinstance(egress_state, dict) or not egress_state.get("egress_id"):
        return None

    if egress_state.get("status") == "completed":
        if run_analysis:
            await _run_analysis_if_ready(session_id)
        return egress_state

    stop_result: Dict[str, Any] = {}
    try:
        stop_result = await livekit_service.stop_egress(egress_state["egress_id"])
    except Exception as exc:
        stop_result = {"error": str(exc)}

    file_result = {}
    file_results = stop_result.get("file_results") or []
    if file_results:
        file_result = file_results[0] or {}

    relative_path = (
        _derive_relative_recording_path(file_result.get("location"))
        or _derive_relative_recording_path(file_result.get("filename"))
        or egress_state.get("relative_path")
    )
    if not relative_path:
        participant["audio_egress"] = {
            **egress_state,
            "status": "completed",
            "ended_at": ended_at or _utc_now_iso(),
            "reason": reason,
            "stop_result": stop_result,
        }
        session_store.save_session(session_id, session)
        if run_analysis:
            await _run_analysis_if_ready(session_id)
        return participant["audio_egress"]

    absolute_recording_path = session_store.recordings_dir / relative_path
    size = file_result.get("size")
    if not size and absolute_recording_path.exists():
        size = absolute_recording_path.stat().st_size

    ended_at_iso = ended_at or _utc_now_iso()
    recording_info = {
        "stream_id": egress_state.get("track_id"),
        "connection_id": egress_state.get("connection_id") or participant.get("connection_id"),
        "file_path": relative_path,
        "has_audio": True,
        "has_video": False,
        "type_of_video": "NONE",
        "start_time_offset_ms": None,
        "end_time_offset_ms": None,
        "size": size,
        "mime_type": _guess_mime_type(relative_path),
        "device_label": "livekit_track_egress",
        "recorded_started_at": egress_state.get("started_at"),
        "recorded_ended_at": ended_at_iso,
    }
    session_store.add_participant_recording_file(
        session_id=session_id,
        participant_id=participant_id,
        recording_info=recording_info,
    )
    session_store.update_recording(
        session_id,
        {
            "mode": "LIVEKIT_TRACK_EGRESS",
            "status": "uploaded",
            "ready_at": _utc_now_iso(),
            "stopped_at": ended_at_iso,
            "reason": None,
        },
    )

    session = session_store.load_session(session_id)
    participant = _find_participant(session, participant_id)
    if participant is None:
        return None

    participant["audio_egress"] = {
        **egress_state,
        "status": "completed",
        "ended_at": ended_at_iso,
        "reason": reason,
        "file_path": relative_path,
        "stop_result": stop_result,
    }
    session_store.save_session(session_id, session)

    if run_analysis:
        await _run_analysis_if_ready(session_id)

    return participant["audio_egress"]


async def stop_session_egresses(session_id: str, *, reason: str) -> None:
    session = session_store.load_session(session_id)
    participant_ids = [
        participant.get("participant_id")
        for participant in session.get("participants", [])
        if participant.get("audio_egress", {}).get("status") in {"starting", "active"}
    ]

    for participant_id in participant_ids:
        if participant_id:
            await stop_participant_egress(
                session_id,
                participant_id,
                reason=reason,
                run_analysis=False,
            )


async def maybe_finalize_session_recording(session_id: str) -> None:
    session = session_store.load_session(session_id)
    has_tracks = any(
        participant.get("recording_files")
        for participant in session.get("participants", [])
    )
    if has_tracks:
        session_store.update_recording(
            session_id,
            {
                "mode": "LIVEKIT_TRACK_EGRESS",
                "status": "uploaded",
                "ready_at": _utc_now_iso(),
                "reason": None,
            },
        )

    await _run_analysis_if_ready(session_id)

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..services import livekit_service
from ..services.meeting_store import meeting_store
from ..services.session_store import session_store

router = APIRouter()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_key(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _resolve_status(meeting: Dict[str, Any], session: Optional[Dict[str, Any]] = None) -> str:
    stored_status = meeting.get("status") or "upcoming"
    if stored_status == "cancelled":
        return "cancelled"

    session_status = (session or {}).get("status")
    if session_status in {"active", "recording"}:
        return "in-progress"
    if session_status == "ended":
        return "completed"

    start_at = _parse_iso(meeting.get("scheduled_start"))
    end_at = _parse_iso(meeting.get("scheduled_end"))
    now = _utc_now()

    if end_at and end_at <= now:
        return "completed"
    if start_at and start_at <= now and (end_at is None or end_at > now):
        return "in-progress"
    return "upcoming"


def _load_linked_session(meeting: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    session_id = meeting.get("session_id")
    if not session_id or not session_store.session_exists(session_id):
        return None
    return session_store.load_session(session_id)


def _compute_recording_summary(session: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    recording = (session or {}).get("recording", {})
    return {
        "status": recording.get("status") or "pending",
        "mode": recording.get("mode"),
        "started_at": recording.get("started_at"),
        "stopped_at": recording.get("stopped_at"),
        "ready_at": recording.get("ready_at"),
        "files_count": len(recording.get("files") or []),
        "archive_path": recording.get("archive_path"),
    }


def _compute_analysis_summary(session: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    analysis = (session or {}).get("speech_analysis", {})
    metrics = analysis.get("metrics") or {}
    ai_analysis = (session or {}).get("ai_analysis", {})
    return {
        "status": analysis.get("status") or "pending",
        "generated_at": analysis.get("generated_at"),
        "segment_count": len(analysis.get("segments") or []),
        "summary_count": len(analysis.get("summary") or []),
        "active_speech_sec": metrics.get("active_speech_sec"),
        "overlap_duration_sec": metrics.get("overlap_duration_sec"),
        "silence_duration_sec": metrics.get("silence_duration_sec"),
        "ai_status": ai_analysis.get("status") or "pending",
        "transcript_available": _ai_transcript_exists(session),
    }


def _build_summary_item(item: Dict[str, Any], total_speaking_sec: float) -> Dict[str, Any]:
    duration = float(item.get("total_speaking_sec") or 0.0)
    percentage = 0.0
    if total_speaking_sec > 0:
        percentage = round((duration / total_speaking_sec) * 100, 2)

    return {
        "participant_id": item.get("participant_id"),
        "display_name": item.get("display_name") or item.get("participant_id"),
        "segment_count": item.get("segment_count") or 0,
        "total_speaking_sec": round(duration, 4),
        "percentage": percentage,
        "first_spoken_sec": item.get("first_spoken_sec"),
        "last_spoken_sec": item.get("last_spoken_sec"),
        "single_segment_count": item.get("single_segment_count") or 0,
        "overlap_segment_count": item.get("overlap_segment_count") or 0,
        "overlap_involved_sec": round(float(item.get("overlap_involved_sec") or 0.0), 4),
        "speaking_percentage_of_recording": item.get("speaking_percentage_of_recording") or 0.0,
        "speaking_percentage_of_active_speech": item.get("speaking_percentage_of_active_speech") or 0.0,
        "overlap_percentage_of_speaking": item.get("overlap_percentage_of_speaking") or 0.0,
    }


def _participant_runtime_map(session: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    runtime: Dict[str, Dict[str, Any]] = {}
    if not session:
        return runtime

    analysis_summary = session.get("speech_analysis", {}).get("summary") or []
    speech_by_name = {
        _normalize_key(item.get("display_name")): item
        for item in analysis_summary
        if _normalize_key(item.get("display_name"))
    }

    for participant in session.get("participants", []):
        name = participant.get("display_name") or participant.get("participant_id")
        normalized = _normalize_key(name)
        if not normalized:
            continue
        speaking = speech_by_name.get(normalized, {})
        runtime[normalized] = {
            "joined_at": participant.get("join_time"),
            "left_at": participant.get("leave_time"),
            "speaking_time": speaking.get("total_speaking_sec") or 0.0,
            "camera_on_time": None,
            "mic_on_time": None,
            "participant_id": participant.get("participant_id"),
            "display_name": name,
        }
    return runtime


def _build_meeting_participants(meeting: Dict[str, Any], session: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    runtime_map = _participant_runtime_map(session)
    participants: List[Dict[str, Any]] = []
    seen_keys: set[str] = set()

    organizer = meeting.get("organizer") or {}
    organizer_name = organizer.get("name")
    organizer_key = _normalize_key(organizer_name)

    def append_participant(base: Dict[str, Any], response_status: str) -> None:
        normalized = _normalize_key(base.get("name"))
        runtime = runtime_map.get(normalized, {})
        seen_keys.add(normalized)
        participants.append(
            {
                "user_id": base.get("user_id"),
                "participant_type": base.get("participant_type") or "external_guest",
                "name": base.get("name") or "Unknown",
                "email": base.get("email"),
                "role": base.get("role") or "member",
                "department": base.get("department") or "Genel",
                "avatar": base.get("avatar"),
                "status": "accepted" if runtime.get("joined_at") else response_status,
                "joined_at": runtime.get("joined_at"),
                "left_at": runtime.get("left_at"),
                "speaking_time": runtime.get("speaking_time"),
                "camera_on_time": runtime.get("camera_on_time"),
                "mic_on_time": runtime.get("mic_on_time"),
                "participant_id": runtime.get("participant_id"),
            }
        )

    if organizer_name:
        append_participant(organizer, "accepted")

    for participant in meeting.get("participants", []):
        if _normalize_key(participant.get("name")) == organizer_key:
            continue
        append_participant(participant, participant.get("response_status") or "pending")

    for normalized, runtime in runtime_map.items():
        if normalized in seen_keys:
            continue
        participants.append(
            {
                "user_id": None,
                "participant_type": "external_guest",
                "name": runtime.get("display_name") or "Unknown",
                "email": None,
                "role": "member",
                "department": "Genel",
                "avatar": None,
                "status": "accepted",
                "joined_at": runtime.get("joined_at"),
                "left_at": runtime.get("left_at"),
                "speaking_time": runtime.get("speaking_time"),
                "camera_on_time": runtime.get("camera_on_time"),
                "mic_on_time": runtime.get("mic_on_time"),
                "participant_id": runtime.get("participant_id"),
            }
        )

    return participants


def _serialize_meeting_list_item(meeting: Dict[str, Any]) -> Dict[str, Any]:
    session = _load_linked_session(meeting)
    participants = _build_meeting_participants(meeting, session)
    return {
        "id": meeting["id"],
        "title": meeting["title"],
        "description": meeting.get("description"),
        "scheduled_start": meeting["scheduled_start"],
        "scheduled_end": meeting["scheduled_end"],
        "status": _resolve_status(meeting, session),
        "organizer": meeting.get("organizer") or {},
        "participants": participants,
        "participants_count": len(participants),
        "agenda": meeting.get("agenda") or [],
        "session_id": meeting.get("session_id"),
        "recording": _compute_recording_summary(session),
        "analysis": _compute_analysis_summary(session),
        "created_at": meeting.get("created_at"),
        "updated_at": meeting.get("updated_at"),
    }


def _serialize_meeting_detail(meeting: Dict[str, Any]) -> Dict[str, Any]:
    session = _load_linked_session(meeting)
    return {
        **_serialize_meeting_list_item(meeting),
        "meeting_id": meeting["id"],
        "participants": _build_meeting_participants(meeting, session),
    }


def _ai_artifact_path(relative_path: Optional[str]) -> Optional[Path]:
    if not relative_path:
        return None

    path = Path(session_store.recordings_dir) / relative_path
    if not path.exists():
        return None
    return path


def _ai_transcript_exists(session: Optional[Dict[str, Any]]) -> bool:
    ai_analysis = (session or {}).get("ai_analysis", {})
    transcript_path = ai_analysis.get("transcript_path")
    if not transcript_path:
        return False
    if not ai_analysis.get("transcript_char_count"):
        return False
    return _ai_artifact_path(transcript_path) is not None


def _load_ai_transcript(session: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    ai_analysis = (session or {}).get("ai_analysis", {})
    transcript_path = _ai_artifact_path(ai_analysis.get("transcript_path"))
    if transcript_path is None:
        return None

    try:
        payload = json.loads(transcript_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    segments = []
    for item in payload.get("segments") or []:
        text = " ".join(str(item.get("text") or "").strip().split())
        speaker = " ".join(
            str(item.get("speaker") or item.get("display_name") or "").strip().split()
        )
        if not text or not speaker:
            continue

        segments.append(
            {
                "speaker": speaker,
                "start": float(item.get("start") or 0.0),
                "end": float(item.get("end") or 0.0),
                "text": text,
            }
        )

    full_text = str(payload.get("full_text") or "").strip()
    if not full_text and not segments:
        return None

    return {
        "generated_at": payload.get("generated_at"),
        "full_text": full_text,
        "segments": segments,
    }


def _serialize_ai_summary(session: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    ai_analysis = (session or {}).get("ai_analysis", {})
    summary = {
        "executiveSummary": ai_analysis.get("executive_summary") or "",
        "keyDecisions": ai_analysis.get("key_decisions") or [],
        "topics": ai_analysis.get("topics") or [],
        "actionItems": ai_analysis.get("action_items") or [],
    }

    if ai_analysis.get("status") == "ready":
        return summary
    if any(summary.values()):
        return summary
    return None


def _serialize_meeting_analysis(meeting: Dict[str, Any]) -> Dict[str, Any]:
    session = _load_linked_session(meeting)
    analysis = (session or {}).get("speech_analysis", {})
    ai_analysis = (session or {}).get("ai_analysis", {})
    metrics = analysis.get("metrics") or {}
    analysis_parameters = analysis.get("analysis_parameters") or {}
    recording = (session or {}).get("recording", {})
    summary = analysis.get("summary") or []
    total_speaking_sec = sum(float(item.get("total_speaking_sec") or 0.0) for item in summary)
    speaking_summary = [_build_summary_item(item, total_speaking_sec) for item in summary]
    joined_participants = len(
        [item for item in (session or {}).get("participants", []) if item.get("join_time")]
    )
    meeting_participants = _build_meeting_participants(meeting, session)
    participant_total = len(meeting_participants)
    average_attendance = round((joined_participants / participant_total) * 100, 2) if participant_total else 0.0

    timeline = []
    for item in analysis.get("segments") or []:
        timeline.append(
            {
                "segment_id": item.get("segment_id"),
                "type": item.get("type"),
                "overlap": bool(item.get("overlap")),
                "start_sec": item.get("start_sec"),
                "end_sec": item.get("end_sec"),
                "duration_sec": item.get("duration_sec"),
                "start_at": item.get("start_at"),
                "end_at": item.get("end_at"),
                "participants": item.get("participants") or [],
            }
        )

    speaking_distribution = [
        {
            "participant_id": item["participant_id"],
            "display_name": item["display_name"],
            "percentage": item["percentage"],
            "duration_sec": item["total_speaking_sec"],
        }
        for item in speaking_summary
    ]

    transcript_payload = _load_ai_transcript(session)
    serialized_summary = _serialize_ai_summary(session)

    return {
        "meeting_id": meeting["id"],
        "session_id": meeting.get("session_id"),
        "status": analysis.get("status") or "pending",
        "generated_at": analysis.get("generated_at"),
        "recording_status": recording.get("status") or "pending",
        "recording": _compute_recording_summary(session),
        "ai_status": ai_analysis.get("status") or "pending",
        "transcript_available": transcript_payload is not None,
        "transcript": transcript_payload,
        "summary": serialized_summary,
        "metrics": metrics,
        "analysis_parameters": analysis_parameters,
        "timeline": timeline,
        "speaking_summary": speaking_summary,
        "analytics": {
            "total_participants": participant_total,
            "average_attendance": average_attendance,
            "recording_duration_sec": metrics.get("recording_duration_sec"),
            "active_speech_sec": metrics.get("active_speech_sec"),
            "active_speech_percentage": metrics.get("active_speech_percentage"),
            "overlap_duration_sec": metrics.get("overlap_duration_sec"),
            "overlap_percentage_of_recording": metrics.get("overlap_percentage_of_recording"),
            "overlap_percentage_of_active_speech": metrics.get("overlap_percentage_of_active_speech"),
            "silence_duration_sec": metrics.get("silence_duration_sec"),
            "silence_percentage": metrics.get("silence_percentage"),
            "average_segment_duration_sec": metrics.get("average_segment_duration_sec"),
            "median_segment_duration_sec": metrics.get("median_segment_duration_sec"),
            "speaking_distribution": speaking_distribution,
            "engagement_score": None,
            "sentiment_breakdown": {
                "positive": 0,
                "neutral": 0,
                "negative": 0,
            },
        },
    }


@router.post("")
async def create_meeting(payload: Dict[str, Any]):
    title = (payload.get("title") or "").strip()
    scheduled_start = payload.get("scheduled_start")
    scheduled_end = payload.get("scheduled_end")
    organizer = payload.get("organizer") or {}

    if not title:
        raise HTTPException(status_code=400, detail="title required")
    if not scheduled_start or not scheduled_end:
        raise HTTPException(status_code=400, detail="scheduled_start and scheduled_end required")
    if not organizer.get("name") or not organizer.get("email"):
        raise HTTPException(status_code=400, detail="organizer name and email required")

    meeting = meeting_store.create_meeting(
        title=title,
        description=(payload.get("description") or "").strip() or None,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        organizer=organizer,
        participants=payload.get("participants") or [],
        agenda=payload.get("agenda") or [],
    )
    return _serialize_meeting_detail(meeting)


@router.get("")
async def list_meetings(
    status: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
):
    meetings = meeting_store.list_meetings(query=q)
    serialized = [_serialize_meeting_list_item(item) for item in meetings]
    if status:
        serialized = [item for item in serialized if item.get("status") == status]
    return {"meetings": serialized}


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str):
    meeting = meeting_store.get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="meeting not found")
    return _serialize_meeting_detail(meeting)


@router.post("/{meeting_id}/start-session")
async def start_meeting_session(meeting_id: str):
    meeting = meeting_store.get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="meeting not found")

    session_id = meeting.get("session_id") or f"meet-{meeting_id}"

    try:
        await livekit_service.create_room(
            room_name=session_id,
            metadata={"meeting_id": meeting_id, "title": meeting.get("title")},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    session = session_store.ensure_session(session_id)
    session["status"] = "active"
    session["meeting_id"] = meeting_id
    session["meeting_title"] = meeting.get("title")
    session_store.save_session(session_id, session)
    meeting_store.update_session_link(meeting_id, session_id)

    return {
        "meeting_id": meeting_id,
        "session_id": session_id,
        "status": "active",
    }


@router.get("/{meeting_id}/analysis")
async def get_meeting_analysis(meeting_id: str):
    meeting = meeting_store.get_meeting(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="meeting not found")
    return _serialize_meeting_analysis(meeting)

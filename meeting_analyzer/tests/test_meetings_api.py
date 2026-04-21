import json
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.routers import meetings as meetings_router
from src.routers import sessions as sessions_router
from src.services.meeting_store import MeetingStore
from src.services.session_store import SessionStore


async def _fake_create_room(*args, **kwargs):
    return {"name": kwargs.get("room_name") or args[0], "status": "ok"}


async def _fake_delete_room(*args, **kwargs):
    return {"status": "deleted"}


async def _fake_stop_session_egresses(*args, **kwargs):
    return None


async def _fake_finalize_recording(*args, **kwargs):
    return None


def build_client(tmp_path: Path, monkeypatch) -> tuple[TestClient, MeetingStore, SessionStore]:
    meeting_store = MeetingStore(str(tmp_path / "meetings.db"))
    session_store = SessionStore(str(tmp_path / "storage"), str(tmp_path / "recordings"))

    monkeypatch.setattr(meetings_router, "meeting_store", meeting_store)
    monkeypatch.setattr(meetings_router, "session_store", session_store)
    monkeypatch.setattr(sessions_router, "meeting_store", meeting_store)
    monkeypatch.setattr(sessions_router, "session_store", session_store)
    monkeypatch.setattr(meetings_router.livekit_service, "create_room", _fake_create_room)
    monkeypatch.setattr(sessions_router.livekit_service, "delete_room", _fake_delete_room)
    monkeypatch.setattr(sessions_router, "stop_session_egresses", _fake_stop_session_egresses)
    monkeypatch.setattr(sessions_router, "maybe_finalize_session_recording", _fake_finalize_recording)

    app = FastAPI()
    app.include_router(meetings_router.router, prefix="/api/meetings")
    app.include_router(sessions_router.router, prefix="/api/sessions")
    client = TestClient(app)
    return client, meeting_store, session_store


def test_create_list_detail_and_analysis_flow(tmp_path, monkeypatch):
    client, meeting_store, session_store = build_client(tmp_path, monkeypatch)

    create_response = client.post(
        "/api/meetings",
        json={
            "title": "Q2 Sync",
            "description": "Roadmap review",
            "scheduled_start": "2026-04-17T09:00:00+00:00",
            "scheduled_end": "2026-04-17T10:00:00+00:00",
            "organizer": {
                "name": "Ahmet Yilmaz",
                "email": "ahmet@example.com",
                "role": "manager",
                "department": "Product",
            },
            "participants": [
                {
                    "name": "Ayse Kaya",
                    "email": "ayse@example.com",
                    "role": "member",
                    "department": "Design",
                    "response_status": "pending",
                }
            ],
            "agenda": [
                {"title": "Roadmap", "duration": 30},
                {"title": "Risks", "duration": 15},
            ],
        },
    )
    assert create_response.status_code == 200
    meeting = create_response.json()
    meeting_id = meeting["id"]
    assert meeting["title"] == "Q2 Sync"
    assert len(meeting["participants"]) == 2

    list_response = client.get("/api/meetings")
    assert list_response.status_code == 200
    assert list_response.json()["meetings"][0]["id"] == meeting_id

    start_response = client.post(f"/api/meetings/{meeting_id}/start-session")
    assert start_response.status_code == 200
    session_id = start_response.json()["session_id"]

    session = session_store.load_session(session_id)
    session["status"] = "ended"
    session["meeting_id"] = meeting_id
    session["participants"] = [
        {
            "participant_id": "par_1",
            "display_name": "Ahmet Yilmaz",
            "join_time": "2026-04-17T09:00:00+00:00",
            "leave_time": "2026-04-17T10:00:00+00:00",
        },
        {
            "participant_id": "par_2",
            "display_name": "Ayse Kaya",
            "join_time": "2026-04-17T09:01:00+00:00",
            "leave_time": "2026-04-17T09:58:00+00:00",
        },
        {
            "participant_id": "EG_demo123",
            "display_name": "EG_demo123",
            "join_time": "2026-04-17T09:00:00+00:00",
            "leave_time": "2026-04-17T10:00:00+00:00",
        },
    ]
    session["recording"]["status"] = "uploaded"
    session["speech_analysis"] = {
        "status": "ready",
        "generated_at": "2026-04-17T10:01:00+00:00",
        "segments": [
            {
                "segment_id": 1,
                "type": "single",
                "overlap": False,
                "start_sec": 0.0,
                "end_sec": 8.5,
                "duration_sec": 8.5,
                "participants": [{"participant_id": "par_1", "display_name": "Ahmet Yilmaz"}],
            }
        ],
        "summary": [
            {
                "participant_id": "par_1",
                "display_name": "Ahmet Yilmaz",
                "segment_count": 1,
                "total_speaking_sec": 8.5,
                "first_spoken_sec": 0.0,
                "last_spoken_sec": 8.5,
            },
            {
                "participant_id": "EG_demo123",
                "display_name": "EG_demo123",
                "segment_count": 0,
                "total_speaking_sec": 0.0,
                "first_spoken_sec": None,
                "last_spoken_sec": None,
            },
        ],
        "metrics": {
            "recording_duration_sec": 12.0,
            "active_speech_sec": 8.5,
            "active_speech_percentage": 70.83,
            "overlap_duration_sec": 0.0,
            "overlap_percentage_of_recording": 0.0,
            "overlap_percentage_of_active_speech": 0.0,
            "silence_duration_sec": 3.5,
            "silence_percentage": 29.17,
            "average_segment_duration_sec": 8.5,
            "median_segment_duration_sec": 8.5,
        },
        "analysis_parameters": {
            "vad_backend": "energy",
            "sample_rate_hz": 16000,
            "frame_length_ms": 25,
            "hop_length_ms": 10,
        },
    }
    transcript_dir = Path(session_store.recordings_dir) / session_id / "analysis" / "ai"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_rel_path = f"{session_id}/analysis/ai/transcript.json"
    summary_rel_path = f"{session_id}/analysis/ai/summary.json"
    (Path(session_store.recordings_dir) / transcript_rel_path).write_text(
        json.dumps(
            {
                "generated_at": "2026-04-17T10:02:00+00:00",
                "full_text": "[Ahmet Yilmaz | 00:00:00 - 00:00:08]\nRoadmap netlestirildi.",
                "segments": [
                    {
                        "speaker": "Ahmet Yilmaz",
                        "start": 0.0,
                        "end": 8.5,
                        "text": "Roadmap netlestirildi.",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (Path(session_store.recordings_dir) / summary_rel_path).write_text(
        json.dumps(
            {
                "generated_at": "2026-04-17T10:02:00+00:00",
                "executiveSummary": "Roadmap ve riskler uzerine yonetici ozeti hazirlandi.",
                "keyDecisions": ["Roadmap onaylandi"],
                "topics": ["Roadmap", "Riskler"],
                "actionItems": [
                    {
                        "id": "action-item-1-roadmap-onayini-paylas",
                        "title": "Roadmap onayini paylas",
                        "priority": "high",
                        "needs_review": False,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    session["ai_analysis"] = {
        "status": "ready",
        "generated_at": "2026-04-17T10:02:00+00:00",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "transcript_path": transcript_rel_path,
        "transcript_segment_count": 1,
        "transcript_char_count": 64,
        "summary_path": summary_rel_path,
        "executive_summary": "Roadmap ve riskler uzerine yonetici ozeti hazirlandi.",
        "key_decisions": ["Roadmap onaylandi"],
        "topics": ["Roadmap", "Riskler"],
        "action_items": [
            {
                "id": "action-item-1-roadmap-onayini-paylas",
                "title": "Roadmap onayini paylas",
                "priority": "high",
                "needs_review": False,
            }
        ],
        "error": None,
        "completed": ["transcription_agent", "summary_agent", "action_item_agent"],
    }
    session_store.save_session(session_id, session)
    meeting_store.update_status(meeting_id, "completed")

    detail_response = client.get(f"/api/meetings/{meeting_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["session_id"] == session_id
    assert detail["analysis"]["status"] == "ready"
    assert detail["analysis"]["ai_status"] == "ready"
    assert detail["analysis"]["transcript_available"] is True
    assert [item["name"] for item in detail["participants"]] == ["Ahmet Yilmaz", "Ayse Kaya"]

    analysis_response = client.get(f"/api/meetings/{meeting_id}/analysis")
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()
    assert analysis["status"] == "ready"
    assert analysis["ai_status"] == "ready"
    assert analysis["transcript_available"] is True
    assert analysis["transcript"]["segments"][0]["speaker"] == "Ahmet Yilmaz"
    assert analysis["summary"]["executiveSummary"] == "Roadmap ve riskler uzerine yonetici ozeti hazirlandi."
    assert analysis["summary"]["actionItems"][0]["title"] == "Roadmap onayini paylas"
    assert analysis["timeline"][0]["participants"][0]["display_name"] == "Ahmet Yilmaz"
    assert analysis["analytics"]["speaking_distribution"][0]["percentage"] == 100.0
    assert len(analysis["speaking_summary"]) == 1
    assert analysis["speaking_summary"][0]["participant_id"] == "par_1"
    assert analysis["analytics"]["total_participants"] == 2
    assert analysis["analytics"]["average_attendance"] == 100.0
    assert analysis["metrics"]["active_speech_sec"] == 8.5
    assert analysis["analytics"]["silence_duration_sec"] == 3.5
    assert analysis["analysis_parameters"]["frame_length_ms"] == 25


def test_stop_session_marks_linked_meeting_completed(tmp_path, monkeypatch):
    client, meeting_store, session_store = build_client(tmp_path, monkeypatch)

    meeting = meeting_store.create_meeting(
        title="Daily",
        description=None,
        scheduled_start="2026-04-17T09:00:00+00:00",
        scheduled_end="2026-04-17T09:15:00+00:00",
        organizer={"name": "Owner", "email": "owner@example.com"},
        participants=[],
        agenda=[],
    )
    meeting_store.update_session_link(meeting["id"], "meet-daily")

    session = session_store.ensure_session("meet-daily")
    session["meeting_id"] = meeting["id"]
    session["status"] = "active"
    session_store.save_session("meet-daily", session)

    response = client.post("/api/sessions/meet-daily/stop")
    assert response.status_code == 200

    updated = meeting_store.get_meeting(meeting["id"])
    assert updated is not None
    assert updated["status"] == "completed"

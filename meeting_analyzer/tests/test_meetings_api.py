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
            }
        ],
    }
    session_store.save_session(session_id, session)
    meeting_store.update_status(meeting_id, "completed")

    detail_response = client.get(f"/api/meetings/{meeting_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["session_id"] == session_id
    assert detail["analysis"]["status"] == "ready"

    analysis_response = client.get(f"/api/meetings/{meeting_id}/analysis")
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()
    assert analysis["status"] == "ready"
    assert analysis["timeline"][0]["participants"][0]["display_name"] == "Ahmet Yilmaz"
    assert analysis["analytics"]["speaking_distribution"][0]["percentage"] == 100.0


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

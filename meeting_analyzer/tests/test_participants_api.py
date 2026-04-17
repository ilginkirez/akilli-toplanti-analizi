import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.routers import participants as participants_router
from src.services.session_store import SessionStore


async def _fake_start_audio_track_egress(*args, **kwargs):
    return {"status": "active", "track_id": kwargs.get("track_id")}


async def _fake_stop_participant_egress(*args, **kwargs):
    return None


async def _fake_finalize(*args, **kwargs):
    return None


def test_update_stream_can_start_audio_egress_from_audio_track_id(tmp_path, monkeypatch):
    store = SessionStore(str(tmp_path / "storage"), str(tmp_path / "recordings"))
    monkeypatch.setattr(participants_router, "session_store", store)
    monkeypatch.setattr(participants_router, "start_audio_track_egress", _fake_start_audio_track_egress)
    monkeypatch.setattr(participants_router, "stop_participant_egress", _fake_stop_participant_egress)
    monkeypatch.setattr(participants_router, "maybe_finalize_session_recording", _fake_finalize)

    app = FastAPI()
    app.include_router(participants_router.router, prefix="/api/participants")
    client = TestClient(app)

    store.register_pending_participant(
        session_id="meeting-a",
        participant_id="par_001",
        display_name="Alice",
    )

    response = client.patch(
        "/api/participants/par_001/stream",
        json={
            "session_id": "meeting-a",
            "connection_id": "con_001",
            "stream_id": "cam_001",
            "audio_track_id": "mic_001",
            "has_audio": True,
            "has_video": True,
            "video_source": "CAMERA",
            "media_type": "livekit_participant",
        },
    )

    assert response.status_code == 200
    session = store.load_session("meeting-a")
    assert session["participants"][0]["connection_id"] == "con_001"
    assert session["streams"]["cam_001"]["participant_id"] == "par_001"

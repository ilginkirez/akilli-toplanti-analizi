import json
import asyncio
import sys
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.session_store import SessionStore


def test_attach_connection_and_stream(tmp_path):
    storage_root = tmp_path / "storage"
    recordings_root = tmp_path / "recordings"
    store = SessionStore(str(storage_root), str(recordings_root))

    store.register_pending_participant(
        session_id="meeting-a",
        participant_id="par_001",
        display_name="Alice",
        device_info={"device_type": "desktop", "browser": "chrome", "os": "windows"},
    )
    store.attach_connection(
        session_id="meeting-a",
        participant_id="par_001",
        connection_id="con_001",
        client_data={"display_name": "Alice"},
        server_data={"participant_id": "par_001"},
    )
    session = store.attach_stream(
        session_id="meeting-a",
        connection_id="con_001",
        stream_id="str_CAM_001",
        audio_enabled=True,
        video_enabled=True,
        video_source="CAMERA",
        media_type="publisher",
    )

    participant = session["participants"][0]
    assert participant["connection_id"] == "con_001"
    assert participant["stream_id"] == "str_CAM_001"
    assert participant["stream_ids"] == ["str_CAM_001"]
    assert session["streams"]["str_CAM_001"]["participant_id"] == "par_001"


def test_pending_participant_stays_inactive_until_connected(tmp_path):
    storage_root = tmp_path / "storage"
    recordings_root = tmp_path / "recordings"
    store = SessionStore(str(storage_root), str(recordings_root))

    session = store.register_pending_participant(
        session_id="meeting-pending",
        participant_id="par_pending",
        display_name="Pending User",
    )
    participant = session["participants"][0]
    assert participant["active"] is False
    assert participant["connection_id"] is None

    session = store.attach_connection(
        session_id="meeting-pending",
        participant_id="par_pending",
        connection_id="PA_real",
        client_data={"display_name": "Pending User"},
        server_data={"participant_id": "par_pending"},
    )
    participant = session["participants"][0]
    assert participant["active"] is True
    assert participant["connection_id"] == "PA_real"


def test_sync_individual_recording_archive_maps_audio_file(tmp_path):
    storage_root = tmp_path / "storage"
    recordings_root = tmp_path / "recordings"
    store = SessionStore(str(storage_root), str(recordings_root))

    store.register_pending_participant(
        session_id="meeting-b",
        participant_id="par_002",
        display_name="Bob",
    )
    store.attach_connection(
        session_id="meeting-b",
        participant_id="par_002",
        connection_id="con_002",
        client_data={"display_name": "Bob"},
        server_data={"participant_id": "par_002", "display_name": "Bob"},
    )
    store.attach_stream(
        session_id="meeting-b",
        connection_id="con_002",
        stream_id="str_CAM_002",
        audio_enabled=True,
        video_enabled=False,
        media_type="publisher",
    )

    archive_path = recordings_root / "meeting-b.zip"
    manifest = {
        "id": "meeting-b",
        "name": "meeting-b",
        "sessionId": "meeting-b",
        "files": [
            {
                "connectionId": "con_002",
                "streamId": "str_CAM_002",
                "size": 1234,
                "clientData": json.dumps({"display_name": "Bob"}),
                "serverData": json.dumps({"participant_id": "par_002", "display_name": "Bob"}),
                "hasAudio": True,
                "hasVideo": False,
                "startTimeOffset": 0,
                "endTimeOffset": 5000,
            }
        ],
    }

    with zipfile.ZipFile(archive_path, "w") as bundle:
        bundle.writestr("meeting-b.json", json.dumps(manifest))
        bundle.writestr("str_CAM_002.webm", b"fake-webm")

    session = store.sync_individual_recording_archive(
        session_id="meeting-b",
        recording_name="meeting-b",
        recording_id="meeting-b",
    )

    assert session is not None
    participant = session["participants"][0]
    assert participant["recording_file"] == "meeting-b/individual/str_CAM_002.webm"
    assert session["recording"]["archive_path"] == "meeting-b.zip"
    assert session["streams"]["str_CAM_002"]["recording_file"] == "meeting-b/individual/str_CAM_002.webm"


def test_finalize_recording_runs_analysis_for_ended_session_with_stale_active_participant(tmp_path, monkeypatch):
    import src.services.egress_recording_service as egress_module

    storage_root = tmp_path / "storage"
    recordings_root = tmp_path / "recordings"
    store = SessionStore(str(storage_root), str(recordings_root))
    monkeypatch.setattr(egress_module, "session_store", store)

    called = []

    def fake_analyze_session(session_id: str):
        called.append(session_id)
        return {"status": "ready"}

    monkeypatch.setattr(
        egress_module.speech_analysis_service,
        "analyze_session",
        fake_analyze_session,
    )

    store.register_pending_participant(
        session_id="meeting-ended",
        participant_id="par_real",
        display_name="Real User",
    )
    session = store.attach_connection(
        session_id="meeting-ended",
        participant_id="par_real",
        connection_id="PA_real",
        client_data={"display_name": "Real User"},
        server_data={"participant_id": "par_real"},
    )
    participant = session["participants"][0]
    participant["active"] = False
    participant["recording_files"] = [
        {
            "file_path": "meeting-ended/individual/real.ogg",
            "has_audio": True,
        }
    ]
    store.save_session("meeting-ended", session)

    store.register_pending_participant(
        session_id="meeting-ended",
        participant_id="par_stale",
        display_name="Stale User",
    )
    session = store.load_session("meeting-ended")
    stale = next(item for item in session["participants"] if item["participant_id"] == "par_stale")
    stale["active"] = True
    session["status"] = "ended"
    session["recording"]["status"] = "uploaded"
    store.save_session("meeting-ended", session)

    asyncio.run(egress_module.maybe_finalize_session_recording("meeting-ended"))

    assert called == ["meeting-ended"]

import json
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

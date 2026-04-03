import json
import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _tone(duration_sec: float, sample_rate: int = 16000) -> np.ndarray:
    timeline = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    return (0.8 * np.sin(2 * np.pi * 220 * timeline)).astype(np.float32)


def test_analyze_session_builds_speaker_timeline(tmp_path, monkeypatch):
    from src.services.session_store import SessionStore
    import src.services.speech_analysis_service as speech_analysis_module

    storage_root = tmp_path / "storage"
    recordings_root = tmp_path / "recordings"
    store = SessionStore(str(storage_root), str(recordings_root))
    monkeypatch.setattr(speech_analysis_module, "session_store", store)

    session_id = "meeting-c"
    alice_path = recordings_root / session_id / "individual" / "alice.wav"
    bob_path = recordings_root / session_id / "individual" / "bob.wav"
    alice_path.parent.mkdir(parents=True, exist_ok=True)
    alice_path.write_bytes(b"placeholder")
    bob_path.write_bytes(b"placeholder")

    service = speech_analysis_module.SpeechAnalysisService(str(recordings_root))
    audio_map = {
        str(alice_path.resolve()): _tone(1.0),
        str(bob_path.resolve()): _tone(1.0),
    }
    sample_rate = service.sample_rate

    class FakeMultiChannelVAD:
        def __init__(self, *args, **kwargs):
            pass

        def process(self, channel_audio_dict):
            segments = []
            for participant_id, audio in channel_audio_dict.items():
                active = np.flatnonzero(np.abs(audio) > 0.05)
                if active.size == 0:
                    continue
                segments.append(
                    {
                        "speaker": participant_id,
                        "start": round(active[0] / sample_rate, 4),
                        "end": round((active[-1] + 1) / sample_rate, 4),
                        "duration": round((active[-1] + 1 - active[0]) / sample_rate, 4),
                        "type": "single",
                        "speakers": [participant_id],
                    }
                )
            return sorted(segments, key=lambda item: item["start"])

    monkeypatch.setattr(
        speech_analysis_module,
        "MultiChannelVAD",
        FakeMultiChannelVAD,
    )
    monkeypatch.setattr(
        service.standardizer,
        "load_and_standardize",
        lambda input_path: audio_map[str(Path(input_path).resolve())],
    )

    store.register_pending_participant(session_id, "par_alice", "ilgin")
    store.attach_connection(session_id, "par_alice", "con_alice")
    store.attach_stream(session_id, "con_alice", "str_alice", audio_enabled=True, video_enabled=False)

    store.register_pending_participant(session_id, "par_bob", "merve")
    store.attach_connection(session_id, "par_bob", "con_bob")
    store.attach_stream(session_id, "con_bob", "str_bob", audio_enabled=True, video_enabled=False)

    session = store.load_session(session_id)
    session["recording"]["started_at"] = "2026-04-03T20:00:00+00:00"
    session["participants"][0]["recording_files"] = [
        {
            "stream_id": "str_alice",
            "connection_id": "con_alice",
            "file_path": f"{session_id}/individual/alice.wav",
            "has_audio": True,
            "has_video": False,
            "start_time_offset_ms": 0,
            "end_time_offset_ms": 1000,
        }
    ]
    session["participants"][0]["recording_file"] = f"{session_id}/individual/alice.wav"
    session["participants"][1]["recording_files"] = [
        {
            "stream_id": "str_bob",
            "connection_id": "con_bob",
            "file_path": f"{session_id}/individual/bob.wav",
            "has_audio": True,
            "has_video": False,
            "start_time_offset_ms": 1500,
            "end_time_offset_ms": 2500,
        }
    ]
    session["participants"][1]["recording_file"] = f"{session_id}/individual/bob.wav"
    store.save_session(session_id, session)

    result = service.analyze_session(session_id)

    assert result["status"] == "ready"
    assert result["segments_path"] == f"{session_id}/analysis/speech_segments.json"
    assert Path(recordings_root / result["segments_path"]).exists()

    alice_segments = [item for item in result["segments"] if item.get("participant_id") == "par_alice"]
    bob_segments = [item for item in result["segments"] if item.get("participant_id") == "par_bob"]

    assert alice_segments
    assert bob_segments
    assert min(item["start_sec"] for item in alice_segments) < 0.2
    assert min(item["start_sec"] for item in bob_segments) > 1.0

    summary = {item["participant_id"]: item for item in result["summary"]}
    assert summary["par_alice"]["display_name"] == "ilgin"
    assert summary["par_bob"]["display_name"] == "merve"
    assert summary["par_alice"]["total_speaking_sec"] > 0
    assert summary["par_bob"]["total_speaking_sec"] > 0

    saved = store.load_session(session_id)
    assert saved["speech_analysis"]["status"] == "ready"
    assert saved["speech_analysis"]["segments"] == result["segments"]

    payload = json.loads((recordings_root / session_id / "analysis" / "speech_segments.json").read_text())
    assert payload["segments"] == result["segments"]

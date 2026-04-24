import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class FakeLLM:
    model = "fake-groq-model"

    def complete_json(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.1):
        if "aksiyon maddesi" in system_prompt:
            return {
                "action_items": [
                    {
                        "task": "Demo sunumunu hazirla",
                        "assignee": "Ayse",
                        "due_date": "2026-04-30",
                        "priority": "high",
                        "confidence": 0.8,
                        "type": "direct",
                        "needs_review": False,
                    }
                ]
            }

        return {
            "executiveSummary": "Toplantida urun demosu ve teslim tarihi ele alindi.",
            "keyDecisions": ["Demo sunumu hazirlanacak"],
            "topics": ["Urun demosu", "Teslim tarihi"],
        }


def test_session_store_defaults_include_ai_analysis(tmp_path):
    from src.services.session_store import SessionStore

    store = SessionStore(str(tmp_path / "storage"), str(tmp_path / "recordings"))
    session = store.ensure_session("session-ai-default")

    assert session["ai_analysis"]["status"] == "pending"
    assert session["ai_analysis"]["provider"] == "groq"
    assert session["ai_analysis"]["transcript_path"] is None


def test_ai_analysis_service_persists_transcript_and_summary(tmp_path, monkeypatch):
    from src.services.meeting_store import MeetingStore
    from src.services.session_store import SessionStore
    import src.services.ai_analysis_service as ai_analysis_module

    storage_root = tmp_path / "storage"
    recordings_root = tmp_path / "recordings"
    store = SessionStore(str(storage_root), str(recordings_root))
    meetings = MeetingStore(str(tmp_path / "meetings.db"))

    monkeypatch.setattr(ai_analysis_module, "session_store", store)
    monkeypatch.setattr(ai_analysis_module, "meeting_store", meetings)

    transcribe_calls: list[str] = []

    def fake_transcribe(filepath: str, *, language: str, speaker: str, participant_id: str | None, offset_sec: float):
        transcribe_calls.append(filepath)
        return [
            {
                "speaker": speaker,
                "participant_id": participant_id,
                "start": round(offset_sec, 4),
                "end": round(offset_sec + 1.2, 4),
                "text": f"{speaker} demo sunumunu hazirlayacak.",
            }
        ]

    monkeypatch.setattr(ai_analysis_module, "transcribe_audio_segments", fake_transcribe)

    session_id = "session-ai-ready"
    audio_dir = recordings_root / session_id / "individual"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / "ayse.wav"
    audio_path.write_bytes(b"fake audio")

    session = store.ensure_session(session_id)
    session["participants"] = [
        {
            "participant_id": "par_ayse",
            "display_name": "Ayse",
            "recording_files": [
                {
                    "file_path": f"{session_id}/individual/ayse.wav",
                    "has_audio": True,
                    "start_time_offset_ms": 0,
                    "end_time_offset_ms": 1200,
                    "recorded_started_at": "2026-04-21T09:00:00+00:00",
                    "recorded_ended_at": "2026-04-21T09:00:01+00:00",
                }
            ],
        }
    ]
    store.save_session(session_id, session)

    service = ai_analysis_module.AIAnalysisService(
        recordings_dir=str(recordings_root),
        llm=FakeLLM(),
    )

    result = service.analyze_session(session_id)

    assert result["status"] == "ready"
    assert result["provider"] == "groq"
    assert result["model"] == "fake-groq-model"
    assert result["transcript_segment_count"] == 1
    assert result["transcript_char_count"] > 0
    assert result["executive_summary"] == "Toplantida urun demosu ve teslim tarihi ele alindi."
    assert result["key_decisions"] == ["Demo sunumu hazirlanacak"]
    assert result["topics"] == ["Urun demosu", "Teslim tarihi"]
    assert result["action_items"][0]["title"] == "Demo sunumunu hazirla"
    assert transcribe_calls == [str(audio_path)]

    transcript_file = recordings_root / result["transcript_path"]
    summary_file = recordings_root / result["summary_path"]
    assert transcript_file.exists()
    assert summary_file.exists()

    transcript_payload = json.loads(transcript_file.read_text(encoding="utf-8"))
    summary_payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert transcript_payload["segments"][0]["speaker"] == "Ayse"
    assert "Ayse" in transcript_payload["full_text"]
    assert summary_payload["executiveSummary"] == result["executive_summary"]

    saved = store.load_session(session_id)
    assert saved["ai_analysis"]["status"] == "ready"
    assert saved["ai_analysis"]["transcript_path"] == result["transcript_path"]

    cached = service.analyze_session(session_id)
    assert cached["generated_at"] == result["generated_at"]
    assert transcribe_calls == [str(audio_path)]


def test_ai_analysis_service_marks_failed_when_no_audio_source(tmp_path, monkeypatch):
    from src.services.meeting_store import MeetingStore
    from src.services.session_store import SessionStore
    import src.services.ai_analysis_service as ai_analysis_module

    store = SessionStore(str(tmp_path / "storage"), str(tmp_path / "recordings"))
    meetings = MeetingStore(str(tmp_path / "meetings.db"))
    monkeypatch.setattr(ai_analysis_module, "session_store", store)
    monkeypatch.setattr(ai_analysis_module, "meeting_store", meetings)

    session_id = "session-ai-failed"
    store.ensure_session(session_id)
    service = ai_analysis_module.AIAnalysisService(
        recordings_dir=str(tmp_path / "recordings"),
        llm=FakeLLM(),
    )

    with pytest.raises(ai_analysis_module.AIAnalysisError):
        service.analyze_session(session_id)

    saved = store.load_session(session_id)
    assert saved["ai_analysis"]["status"] == "failed"
    assert "uygun ses kaydi" in saved["ai_analysis"]["error"]


def test_ai_analysis_service_uses_local_speech_timeline_when_available(tmp_path, monkeypatch):
    from src.services.meeting_store import MeetingStore
    from src.services.session_store import SessionStore
    import src.services.ai_analysis_service as ai_analysis_module

    storage_root = tmp_path / "storage"
    recordings_root = tmp_path / "recordings"
    store = SessionStore(str(storage_root), str(recordings_root))
    meetings = MeetingStore(str(tmp_path / "meetings.db"))

    monkeypatch.setattr(ai_analysis_module, "session_store", store)
    monkeypatch.setattr(ai_analysis_module, "meeting_store", meetings)

    clip_calls: list[tuple[str, float, float]] = []

    def fake_transcribe_clip(
        filepath: str,
        *,
        start_sec: float,
        end_sec: float,
        language: str,
        pad_start_sec: float,
        pad_end_sec: float,
    ) -> str:
        clip_calls.append((filepath, round(start_sec, 2), round(end_sec, 2)))
        if start_sec < 2.0:
            return "Ayse ilk konusma bolumu."
        return "Mehmet ikinci konusma bolumu."

    monkeypatch.setattr(ai_analysis_module, "transcribe_audio_clip_text", fake_transcribe_clip)

    def fail_whole_file(*args, **kwargs):
        raise AssertionError("whole-file transcription fallback should not be used")

    monkeypatch.setattr(ai_analysis_module, "transcribe_audio_segments", fail_whole_file)

    session_id = "session-ai-local-timeline"
    audio_dir = recordings_root / session_id / "individual"
    audio_dir.mkdir(parents=True, exist_ok=True)
    ayse_path = audio_dir / "ayse.wav"
    mehmet_path = audio_dir / "mehmet.wav"
    ayse_path.write_bytes(b"fake audio")
    mehmet_path.write_bytes(b"fake audio")

    session = store.ensure_session(session_id)
    session["participants"] = [
        {
            "participant_id": "par_ayse",
            "display_name": "Ayse",
            "recording_files": [
                {
                    "file_path": f"{session_id}/individual/ayse.wav",
                    "has_audio": True,
                    "start_time_offset_ms": 0,
                    "recorded_started_at": "2026-04-21T09:00:00+00:00",
                    "recorded_ended_at": "2026-04-21T09:00:04+00:00",
                }
            ],
        },
        {
            "participant_id": "par_mehmet",
            "display_name": "Mehmet",
            "recording_files": [
                {
                    "file_path": f"{session_id}/individual/mehmet.wav",
                    "has_audio": True,
                    "start_time_offset_ms": 0,
                    "recorded_started_at": "2026-04-21T09:00:00+00:00",
                    "recorded_ended_at": "2026-04-21T09:00:04+00:00",
                }
            ],
        },
    ]
    session["speech_analysis"] = {
        **session["speech_analysis"],
        "status": "ready",
        "generated_at": "2026-04-21T09:05:00+00:00",
        "segments": [
            {
                "segment_id": 1,
                "type": "single",
                "start_sec": 0.0,
                "end_sec": 0.8,
                "participants": [{"participant_id": "par_ayse", "display_name": "Ayse"}],
                "participant_id": "par_ayse",
                "display_name": "Ayse",
            },
            {
                "segment_id": 2,
                "type": "single",
                "start_sec": 0.95,
                "end_sec": 1.4,
                "participants": [{"participant_id": "par_ayse", "display_name": "Ayse"}],
                "participant_id": "par_ayse",
                "display_name": "Ayse",
            },
            {
                "segment_id": 3,
                "type": "single",
                "start_sec": 2.2,
                "end_sec": 3.0,
                "participants": [{"participant_id": "par_mehmet", "display_name": "Mehmet"}],
                "participant_id": "par_mehmet",
                "display_name": "Mehmet",
            },
        ],
    }
    store.save_session(session_id, session)

    service = ai_analysis_module.AIAnalysisService(
        recordings_dir=str(recordings_root),
        llm=FakeLLM(),
    )

    result = service.analyze_session(session_id)

    assert result["status"] == "ready"
    assert clip_calls == [
        (str(ayse_path), 0.0, 1.4),
        (str(mehmet_path), 2.2, 3.0),
    ]

    transcript_file = recordings_root / result["transcript_path"]
    transcript_payload = json.loads(transcript_file.read_text(encoding="utf-8"))

    assert transcript_payload["segments"] == [
        {
            "speaker": "Ayse",
            "participant_id": "par_ayse",
            "start": 0.0,
            "end": 1.4,
            "text": "Ayse ilk konusma bolumu.",
            "source_segment_ids": [1, 2],
        },
        {
            "speaker": "Mehmet",
            "participant_id": "par_mehmet",
            "start": 2.2,
            "end": 3.0,
            "text": "Mehmet ikinci konusma bolumu.",
            "source_segment_ids": [3],
        },
    ]
    assert "[Ayse | 00:00:00 - 00:00:01]" in transcript_payload["full_text"]
    assert "[Mehmet | 00:00:02 - 00:00:03]" in transcript_payload["full_text"]

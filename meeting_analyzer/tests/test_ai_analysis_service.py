import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class FakeLLM:
    model = "fake-groq-model"

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
    ):
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
    assert session["ai_analysis"]["notifications_sent"] == []
    assert session["ai_analysis"]["notification_status"] is None
    assert session["ai_analysis"]["notification_fingerprint"] is None


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
    monkeypatch.setattr(ai_analysis_module, "notify_assignees", lambda **kwargs: [])

    transcribe_calls: list[str] = []

    def fake_transcribe(
        filepath: str,
        *,
        speaker: str,
        participant_id: str | None,
        offset_sec: float,
    ):
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
    assert result["notifications_sent"] == []
    assert result["notification_status"] == "skipped"
    assert "notification_agent" in result["completed"]
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
    assert saved["ai_analysis"]["notification_status"] == "skipped"

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


def test_notify_action_items_skips_duplicate_notifications(tmp_path, monkeypatch):
    from src.services.meeting_store import MeetingStore
    from src.services.session_store import SessionStore
    import src.services.ai_analysis_service as ai_analysis_module

    store = SessionStore(str(tmp_path / "storage"), str(tmp_path / "recordings"))
    meetings = MeetingStore(str(tmp_path / "meetings.db"))
    monkeypatch.setattr(ai_analysis_module, "session_store", store)
    monkeypatch.setattr(ai_analysis_module, "meeting_store", meetings)

    send_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        ai_analysis_module,
        "notify_assignees",
        lambda **kwargs: send_calls.append(kwargs) or [],
    )

    service = ai_analysis_module.AIAnalysisService(
        recordings_dir=str(tmp_path / "recordings"),
        llm=FakeLLM(),
    )

    session_id = "session-ai-duplicate"
    action_items = [
        {
            "task": "Sunumu hazirla",
            "assigned_to_user_id": "usr-ayse",
            "due_date": "2026-04-30",
            "priority": "high",
            "needs_review": False,
            "ambiguous": False,
        }
    ]
    meeting_participants = [
        {
            "user_id": "usr-ayse",
            "name": "Ayse",
            "email": "ayse@example.com",
        }
    ]
    previous_notifications = [
        {
            "user_id": "usr-ayse",
            "email": "ayse@example.com",
            "name": "Ayse",
            "tasks_count": 1,
        }
    ]
    fingerprint = service._notification_fingerprint(
        action_items=action_items,
        meeting_participants=meeting_participants,
    )

    session = store.ensure_session(session_id)
    session["ai_analysis"]["notification_fingerprint"] = fingerprint
    session["ai_analysis"]["notifications_sent"] = previous_notifications
    store.save_session(session_id, session)

    result = service._notify_action_items(
        session_id=session_id,
        action_items=action_items,
        meeting_participants=meeting_participants,
    )

    assert result["notification_status"] == "skipped_duplicate"
    assert result["notifications_sent"] == previous_notifications
    assert result["notification_fingerprint"] == fingerprint
    assert send_calls == []


def test_ai_analysis_service_runs_langgraph_pipeline(tmp_path, monkeypatch):
    from src.services.meeting_store import MeetingStore
    from src.services.session_store import SessionStore
    import src.services.ai_analysis_service as ai_analysis_module

    store = SessionStore(str(tmp_path / "storage"), str(tmp_path / "recordings"))
    meetings = MeetingStore(str(tmp_path / "meetings.db"))

    monkeypatch.setattr(ai_analysis_module, "session_store", store)
    monkeypatch.setattr(ai_analysis_module, "meeting_store", meetings)

    service = ai_analysis_module.AIAnalysisService(
        recordings_dir=str(tmp_path / "recordings"),
        llm=FakeLLM(),
    )

    monkeypatch.setattr(
        service,
        "_build_transcript",
        lambda session, sources: (
            [{"speaker": "Ayse", "start": 0.0, "end": 1.0, "text": "Merhaba"}],
            "Merhaba",
        ),
    )
    monkeypatch.setattr(
        service,
        "_notify_action_items",
        lambda **kwargs: {
            "notifications_sent": [
                {
                    "user_id": "usr-ayse",
                    "email": "ayse@example.com",
                    "name": "Ayse",
                    "tasks_count": 1,
                }
            ],
            "notification_status": "sent",
            "notification_error": None,
            "notification_fingerprint": "fp-1",
        },
    )

    state = service._run_analysis_graph(
        session_id="session-graph",
        session={"meeting_id": "m-graph"},
        sources=[],
        meeting_date="2026-04-24",
        meeting_participants=[
            {"user_id": "usr-ayse", "name": "Ayse", "email": "ayse@example.com"}
        ],
    )

    assert state["full_text"] == "Merhaba"
    assert (
        state["summary_result"]["executiveSummary"]
        == "Toplantida urun demosu ve teslim tarihi ele alindi."
    )
    assert state["action_items"][0]["task"] == "Demo sunumunu hazirla"
    assert state["summary_output"].executiveSummary == (
        "Toplantida urun demosu ve teslim tarihi ele alindi."
    )
    assert state["summary_output"].actionItems[0].title == "Demo sunumunu hazirla"
    assert state["notification_status"] == "sent"
    assert state["notification_fingerprint"] == "fp-1"
    assert state["notifications_sent"][0]["user_id"] == "usr-ayse"

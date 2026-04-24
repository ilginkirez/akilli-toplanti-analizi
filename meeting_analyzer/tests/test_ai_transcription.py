import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_transcription_relaxed_filter_accepts_short_low_confidence_segment(tmp_path, monkeypatch):
    import src.services.ai_transcription as transcription

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake audio")

    monkeypatch.setattr(transcription, "_preprocess_audio", lambda path: path)

    def fake_run_transcription(path: str, language: str, *, vad_filter: bool = True):
        return [
            SimpleNamespace(
                text="merhaba",
                no_speech_prob=0.62,
                avg_logprob=-1.3,
                start=0.0,
                end=1.1,
            )
        ]

    monkeypatch.setattr(transcription, "_run_transcription", fake_run_transcription)

    items = transcription.transcribe_audio_segments(
        str(audio_path),
        speaker="Ilgin",
        participant_id="par_1",
        offset_sec=0.4,
    )

    assert items == [
        {
            "speaker": "Ilgin",
            "participant_id": "par_1",
            "start": 0.4,
            "end": 1.5,
            "text": "merhaba",
        }
    ]


def test_transcription_retries_without_vad_when_first_pass_empty(tmp_path, monkeypatch):
    import src.services.ai_transcription as transcription

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake audio")

    monkeypatch.setattr(transcription, "_preprocess_audio", lambda path: path)

    calls: list[bool] = []

    def fake_run_transcription(path: str, language: str, *, vad_filter: bool = True):
        calls.append(vad_filter)
        if vad_filter:
            return []
        return [
            SimpleNamespace(
                text="bugun raporu bitiriyorum",
                no_speech_prob=0.2,
                avg_logprob=-0.4,
                start=0.0,
                end=1.9,
            )
        ]

    monkeypatch.setattr(transcription, "_run_transcription", fake_run_transcription)

    items = transcription.transcribe_audio_segments(
        str(audio_path),
        speaker="Ilgin",
        participant_id="par_1",
        offset_sec=0.0,
    )

    assert calls == [True, False]
    assert items[0]["text"] == "bugun raporu bitiriyorum"


def test_run_transcription_uses_groq_verbose_segments(monkeypatch):
    import src.services.ai_transcription as transcription

    monkeypatch.setattr(
        transcription,
        "_request_transcription",
        lambda path, language: {
            "text": "Merhaba dunya",
            "segments": [
                {
                    "text": "Merhaba dunya",
                    "start": 1.25,
                    "end": 2.75,
                }
            ],
        },
    )

    segments = transcription._run_transcription("dummy.webm", "tr")

    assert segments == [
        {
            "text": "Merhaba dunya",
            "start": 1.25,
            "end": 2.75,
        }
    ]


def test_run_transcription_falls_back_to_text_when_segments_missing(monkeypatch):
    import src.services.ai_transcription as transcription

    monkeypatch.setattr(
        transcription,
        "_request_transcription",
        lambda path, language: {
            "text": "Toplanti basliyor",
            "duration": 4.2,
            "segments": [],
        },
    )

    segments = transcription._run_transcription("dummy.webm", "tr")

    assert segments == [
        {
            "text": "Toplanti basliyor",
            "start": 0.0,
            "end": 4.2,
        }
    ]


def test_transcribe_audio_text_returns_cleaned_payload_text(tmp_path, monkeypatch):
    import src.services.ai_transcription as transcription

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake audio")

    monkeypatch.setattr(transcription, "_preprocess_audio", lambda path: path)
    monkeypatch.setattr(
        transcription,
        "_request_transcription",
        lambda path, language: {"text": "  Merhaba   dunya  "},
    )

    text = transcription.transcribe_audio_text(str(audio_path), language="tr")

    assert text == "Merhaba dunya"


def test_transcribe_audio_clip_text_returns_empty_for_invalid_window(tmp_path):
    import src.services.ai_transcription as transcription

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"fake audio")

    text = transcription.transcribe_audio_clip_text(
        str(audio_path),
        start_sec=4.0,
        end_sec=4.0,
        language="tr",
    )

    assert text == ""

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

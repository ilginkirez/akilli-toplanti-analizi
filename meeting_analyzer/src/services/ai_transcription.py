import os
import re
import subprocess
import tempfile
from typing import Any


MODEL_NAME = os.getenv("AI_TRANSCRIBE_MODEL", "medium").strip() or "medium"
DEFAULT_LANGUAGE = "tr"
BEAM_SIZE = 5

MIN_SEGMENT_CHARS = 3
MIN_SEGMENT_WORDS = 2
MAX_NO_SPEECH_PROB = 0.50
MIN_AVG_LOGPROB = -1.0

_model = None


class TranscriptionError(Exception):
    pass


def _get_model():
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover
            raise TranscriptionError(
                "faster-whisper kurulu degil. requirements.txt guncellenmeli."
            ) from exc

        _model = WhisperModel(
            MODEL_NAME,
            device="auto",
            compute_type="default",
        )
    return _model


def _preprocess_audio(input_path: str) -> str:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Ses dosyasi bulunamadi: {input_path}")

    temp_dir = os.path.dirname(input_path) or "."
    temp_fd, temp_path = tempfile.mkstemp(suffix=".wav", dir=temp_dir)
    os.close(temp_fd)

    cmd = [
        "ffmpeg",
        "-i",
        input_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        "-y",
        temp_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return input_path
    except subprocess.TimeoutExpired as exc:  # pragma: no cover
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise TranscriptionError("FFmpeg islemi zaman asimina ugradi.") from exc

    if result.returncode != 0:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise TranscriptionError(
            f"FFmpeg islemi basarisiz oldu: {result.stderr[:500]}"
        )

    return temp_path


def _clean_transcript(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def _is_segment_meaningful(text: str) -> bool:
    if not text:
        return False

    text = text.strip()
    if len(text) < MIN_SEGMENT_CHARS:
        return False

    words = text.split()
    if len(words) < MIN_SEGMENT_WORDS:
        return False

    alpha_count = sum(1 for ch in text if ch.isalpha())
    if alpha_count < 2:
        return False

    short_word_count = sum(
        1
        for word in words
        if len(re.sub(r"[^\wçğıöşüÇĞIİÖŞÜ]", "", word)) <= 1
    )
    if words and (short_word_count / len(words)) > 0.6:
        return False

    return True


def _run_transcription(audio_path: str, language: str):
    model = _get_model()
    segments, _ = model.transcribe(
        audio_path,
        language=language,
        beam_size=BEAM_SIZE,
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 300,
            "speech_pad_ms": 100,
        },
    )
    return segments


def transcribe_audio_segments(
    filepath: str,
    *,
    language: str = DEFAULT_LANGUAGE,
    speaker: str,
    participant_id: str | None = None,
    offset_sec: float = 0.0,
) -> list[dict[str, Any]]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Ses dosyasi bulunamadi: {filepath}")

    processed_path = _preprocess_audio(filepath)
    is_temp_file = processed_path != filepath
    items: list[dict[str, Any]] = []

    try:
        segments = _run_transcription(processed_path, language)
        for segment in segments:
            text = _clean_transcript((getattr(segment, "text", "") or "").strip())
            no_speech_prob = getattr(segment, "no_speech_prob", 0.0)
            avg_logprob = getattr(segment, "avg_logprob", -999.0)

            if not _is_segment_meaningful(text):
                continue
            if no_speech_prob > MAX_NO_SPEECH_PROB:
                continue
            if avg_logprob < MIN_AVG_LOGPROB:
                continue

            items.append(
                {
                    "speaker": speaker,
                    "participant_id": participant_id,
                    "start": round(float(getattr(segment, "start", 0.0)) + offset_sec, 4),
                    "end": round(float(getattr(segment, "end", 0.0)) + offset_sec, 4),
                    "text": text,
                }
            )
    finally:
        if is_temp_file and os.path.exists(processed_path):
            os.remove(processed_path)

    return items

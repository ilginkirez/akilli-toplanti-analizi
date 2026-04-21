import logging
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
RELAXED_MIN_SEGMENT_WORDS = 1
RELAXED_MAX_NO_SPEECH_PROB = 0.75
RELAXED_MIN_AVG_LOGPROB = -1.6

_model = None
logger = logging.getLogger("meeting_analyzer.ai_transcription")


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


def _is_segment_meaningful(text: str, *, min_words: int = MIN_SEGMENT_WORDS) -> bool:
    if not text:
        return False

    text = text.strip()
    if len(text) < MIN_SEGMENT_CHARS:
        return False

    words = text.split()
    if len(words) < min_words:
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


def _run_transcription(audio_path: str, language: str, *, vad_filter: bool = True):
    model = _get_model()
    segments, _ = model.transcribe(
        audio_path,
        language=language,
        beam_size=BEAM_SIZE,
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=vad_filter,
        vad_parameters={
            "min_silence_duration_ms": 300,
            "speech_pad_ms": 100,
        },
    )
    return segments


def _segment_to_item(
    segment: Any,
    *,
    speaker: str,
    participant_id: str | None,
    offset_sec: float,
    min_words: int,
    max_no_speech_prob: float,
    min_avg_logprob: float,
) -> dict[str, Any] | None:
    text = _clean_transcript((getattr(segment, "text", "") or "").strip())
    no_speech_prob = getattr(segment, "no_speech_prob", 0.0)
    avg_logprob = getattr(segment, "avg_logprob", -999.0)

    if not _is_segment_meaningful(text, min_words=min_words):
        return None
    if no_speech_prob > max_no_speech_prob:
        return None
    if avg_logprob < min_avg_logprob:
        return None

    return {
        "speaker": speaker,
        "participant_id": participant_id,
        "start": round(float(getattr(segment, "start", 0.0)) + offset_sec, 4),
        "end": round(float(getattr(segment, "end", 0.0)) + offset_sec, 4),
        "text": text,
    }


def _collect_items(
    segments: list[Any],
    *,
    speaker: str,
    participant_id: str | None,
    offset_sec: float,
    relaxed: bool = False,
) -> list[dict[str, Any]]:
    if relaxed:
        min_words = RELAXED_MIN_SEGMENT_WORDS
        max_no_speech_prob = RELAXED_MAX_NO_SPEECH_PROB
        min_avg_logprob = RELAXED_MIN_AVG_LOGPROB
    else:
        min_words = MIN_SEGMENT_WORDS
        max_no_speech_prob = MAX_NO_SPEECH_PROB
        min_avg_logprob = MIN_AVG_LOGPROB

    items: list[dict[str, Any]] = []
    for segment in segments:
        item = _segment_to_item(
            segment,
            speaker=speaker,
            participant_id=participant_id,
            offset_sec=offset_sec,
            min_words=min_words,
            max_no_speech_prob=max_no_speech_prob,
            min_avg_logprob=min_avg_logprob,
        )
        if item is not None:
            items.append(item)
    return items


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
    try:
        segments = list(_run_transcription(processed_path, language, vad_filter=True))
        items = _collect_items(
            segments,
            speaker=speaker,
            participant_id=participant_id,
            offset_sec=offset_sec,
            relaxed=False,
        )
        if items:
            return items

        relaxed_items = _collect_items(
            segments,
            speaker=speaker,
            participant_id=participant_id,
            offset_sec=offset_sec,
            relaxed=True,
        )
        if relaxed_items:
            logger.info(
                "Transkripsiyon gevsek filtre fallback'i kullanildi: speaker=%s segment=%d",
                speaker,
                len(relaxed_items),
            )
            return relaxed_items

        fallback_segments = list(_run_transcription(processed_path, language, vad_filter=False))
        fallback_items = _collect_items(
            fallback_segments,
            speaker=speaker,
            participant_id=participant_id,
            offset_sec=offset_sec,
            relaxed=True,
        )
        if fallback_items:
            logger.info(
                "Transkripsiyon VAD kapali fallback'i kullanildi: speaker=%s segment=%d",
                speaker,
                len(fallback_items),
            )
        return fallback_items
    finally:
        if is_temp_file and os.path.exists(processed_path):
            os.remove(processed_path)

import logging
import mimetypes
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx


MODEL_NAME = os.getenv("AI_TRANSCRIBE_MODEL", "whisper-large-v3").strip() or "whisper-large-v3"
TRANSCRIBE_API_URL = (
    os.getenv("AI_TRANSCRIBE_API_URL", "https://api.groq.com/openai/v1/audio/transcriptions").strip()
    or "https://api.groq.com/openai/v1/audio/transcriptions"
)
DEFAULT_LANGUAGE = "tr"
REQUEST_TIMEOUT_SEC = float(os.getenv("AI_TRANSCRIBE_TIMEOUT_SEC", "180"))
FORCE_PREPROCESS = os.getenv("AI_TRANSCRIBE_FORCE_PREPROCESS", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SUPPORTED_UPLOAD_SUFFIXES = {
    ".flac",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".m4a",
    ".ogg",
    ".wav",
    ".webm",
}

MIN_SEGMENT_CHARS = 3
MIN_SEGMENT_WORDS = 2
MAX_NO_SPEECH_PROB = 0.50
MIN_AVG_LOGPROB = -1.0
RELAXED_MIN_SEGMENT_WORDS = 1
RELAXED_MAX_NO_SPEECH_PROB = 0.75
RELAXED_MIN_AVG_LOGPROB = -1.6

logger = logging.getLogger("meeting_analyzer.ai_transcription")


class TranscriptionError(Exception):
    pass


def _run_ffmpeg(cmd: list[str], *, timeout: int = 120) -> None:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise TranscriptionError("FFmpeg bulunamadi.") from exc
    except subprocess.TimeoutExpired as exc:  # pragma: no cover
        raise TranscriptionError("FFmpeg islemi zaman asimina ugradi.") from exc

    if result.returncode != 0:
        raise TranscriptionError(
            f"FFmpeg islemi basarisiz oldu: {result.stderr[:500]}"
        )


def _preprocess_audio(input_path: str) -> str:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Ses dosyasi bulunamadi: {input_path}")

    suffix = Path(input_path).suffix.lower()
    if suffix in SUPPORTED_UPLOAD_SUFFIXES and not FORCE_PREPROCESS:
        return input_path

    temp_dir = os.path.dirname(input_path) or "."
    temp_fd, temp_path = tempfile.mkstemp(suffix=".flac", dir=temp_dir)
    os.close(temp_fd)

    cmd = [
        "ffmpeg",
        "-i",
        input_path,
        "-vn",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "flac",
        "-y",
        temp_path,
    ]

    try:
        _run_ffmpeg(cmd, timeout=120)
    except TranscriptionError as exc:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if "FFmpeg bulunamadi" in str(exc):
            raise TranscriptionError(
                "FFmpeg bulunamadi; dosya Groq STT icin desteklenen bir formata donusturulemedi."
            ) from exc
        raise

    return temp_path


def _clean_transcript(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _segment_value(segment: Any, key: str, default: Any = None) -> Any:
    if isinstance(segment, dict):
        return segment.get(key, default)
    return getattr(segment, key, default)


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
        if len(re.sub(r"[^\w]", "", word, flags=re.UNICODE)) <= 1
    )
    if words and (short_word_count / len(words)) > 0.6:
        return False

    return True


def _extract_response_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or error.get("type") or "").strip()
            if message:
                return message
        message = str(payload.get("message") or "").strip()
        if message:
            return message

    text = response.text.strip()
    if text:
        return text[:500]
    return f"HTTP {response.status_code}"


def _request_transcription(audio_path: str, language: str) -> dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise TranscriptionError("GROQ_API_KEY tanimli degil.")

    mime_type = mimetypes.guess_type(audio_path)[0] or "application/octet-stream"
    data = {
        "model": MODEL_NAME,
        "response_format": "verbose_json",
        "timestamp_granularities[]": "segment",
        "temperature": "0",
    }
    if language:
        data["language"] = language

    try:
        with open(audio_path, "rb") as file_handle:
            response = httpx.post(
                TRANSCRIBE_API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                data=data,
                files=[("file", (Path(audio_path).name, file_handle, mime_type))],
                timeout=REQUEST_TIMEOUT_SEC,
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = _extract_response_error(exc.response)
        raise TranscriptionError(f"Groq transkripsiyon istegi basarisiz: {detail}") from exc
    except httpx.HTTPError as exc:
        raise TranscriptionError(f"Groq transkripsiyon istegi basarisiz: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise TranscriptionError("Groq transkripsiyon yaniti JSON degildi.") from exc

    if not isinstance(payload, dict):
        raise TranscriptionError("Groq transkripsiyon yaniti beklenen nesne formatinda degildi.")
    return payload


def _extract_audio_clip(
    input_path: str,
    *,
    start_sec: float,
    end_sec: float,
    output_suffix: str = ".flac",
) -> str:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Ses dosyasi bulunamadi: {input_path}")

    clip_start = max(0.0, float(start_sec))
    clip_end = max(clip_start, float(end_sec))
    if clip_end <= clip_start:
        return ""

    temp_dir = os.path.dirname(input_path) or "."
    temp_fd, temp_path = tempfile.mkstemp(suffix=output_suffix, dir=temp_dir)
    os.close(temp_fd)

    cmd = [
        "ffmpeg",
        "-ss",
        f"{clip_start:.4f}",
        "-t",
        f"{clip_end - clip_start:.4f}",
        "-i",
        input_path,
        "-vn",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "flac",
        "-y",
        temp_path,
    ]

    try:
        _run_ffmpeg(cmd, timeout=120)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

    return temp_path


def _payload_to_text(payload: dict[str, Any]) -> str:
    return _clean_transcript(str(payload.get("text") or ""))


def _run_transcription(audio_path: str, language: str, *, vad_filter: bool = True):
    del vad_filter

    payload = _request_transcription(audio_path, language)
    segments = payload.get("segments") or []
    if isinstance(segments, list) and segments:
        return segments

    text = _payload_to_text(payload)
    if not text:
        return []

    duration = _coerce_float(payload.get("duration")) or 0.0
    logger.info(
        "Groq verbose_json segment donmedi; tam metin tek segment olarak kullanildi. model=%s",
        MODEL_NAME,
    )
    return [
        {
            "text": text,
            "start": 0.0,
            "end": duration,
        }
    ]


def transcribe_audio_text(
    filepath: str,
    *,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Ses dosyasi bulunamadi: {filepath}")

    processed_path = _preprocess_audio(filepath)
    is_temp_file = processed_path != filepath
    try:
        payload = _request_transcription(processed_path, language)
        text = _payload_to_text(payload)
        if not text:
            return ""
        return text if _is_segment_meaningful(text, min_words=1) else ""
    finally:
        if is_temp_file and os.path.exists(processed_path):
            os.remove(processed_path)


def transcribe_audio_clip_text(
    filepath: str,
    *,
    start_sec: float,
    end_sec: float,
    language: str = DEFAULT_LANGUAGE,
    pad_start_sec: float = 0.0,
    pad_end_sec: float = 0.0,
) -> str:
    clip_start = max(0.0, float(start_sec) - max(0.0, float(pad_start_sec)))
    clip_end = max(clip_start, float(end_sec) + max(0.0, float(pad_end_sec)))
    if clip_end <= clip_start:
        return ""

    clip_path = _extract_audio_clip(
        filepath,
        start_sec=clip_start,
        end_sec=clip_end,
        output_suffix=".flac",
    )
    if not clip_path:
        return ""

    try:
        return transcribe_audio_text(
            clip_path,
            language=language,
        )
    finally:
        if os.path.exists(clip_path):
            os.remove(clip_path)


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
    text = _clean_transcript(str(_segment_value(segment, "text", "") or "").strip())
    no_speech_prob = _coerce_float(_segment_value(segment, "no_speech_prob"))
    avg_logprob = _coerce_float(_segment_value(segment, "avg_logprob"))

    if not _is_segment_meaningful(text, min_words=min_words):
        return None
    if no_speech_prob is not None and no_speech_prob > max_no_speech_prob:
        return None
    if avg_logprob is not None and avg_logprob < min_avg_logprob:
        return None

    start = _coerce_float(_segment_value(segment, "start")) or 0.0
    end = _coerce_float(_segment_value(segment, "end"))
    if end is None:
        end = start

    return {
        "speaker": speaker,
        "participant_id": participant_id,
        "start": round(start + offset_sec, 4),
        "end": round(end + offset_sec, 4),
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
                "Transkripsiyon ikinci deneme fallback'i kullanildi: speaker=%s segment=%d",
                speaker,
                len(fallback_items),
            )
        return fallback_items
    finally:
        if is_temp_file and os.path.exists(processed_path):
            os.remove(processed_path)

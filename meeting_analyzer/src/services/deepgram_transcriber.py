"""
deepgram_transcriber.py
-----------------------
Deepgram Nova-2 ile ses dosyasını transkribe eder.
Sadece benchmark amaçlı kullanılır.
REST API kullanır (SDK sürüm bağımsız).
"""

import os
import logging
import httpx

logger = logging.getLogger("meeting_analyzer.deepgram_transcriber")

DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"


def transcribe_with_deepgram(audio_path: str, language: str = "en") -> str:
    """
    Deepgram Nova-2 modeli ile ses dosyasını transkribe eder.

    Args:
        audio_path: Ses dosyasının yolu (.wav, .mp3, .flac vb.)
        language: Dil kodu (varsayılan: "en")

    Returns:
        Transkribe edilmiş metin (string)
    """
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise ValueError("DEEPGRAM_API_KEY ortam değişkeni tanımlı değil.")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Ses dosyası bulunamadı: {audio_path}")

    # Ses dosyasını oku
    with open(audio_path, "rb") as f:
        audio_data = f.read()

    # Content type belirle
    ext = os.path.splitext(audio_path)[1].lower()
    content_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
    }
    content_type = content_types.get(ext, "audio/wav")

    # API parametreleri
    params = {
        "model": "nova-2",
        "language": language,
        "smart_format": "false",
        "punctuate": "false",
        "diarize": "false",
    }

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": content_type,
    }

    logger.info(f"Deepgram Nova-2 transkripsiyon başlatılıyor: {audio_path}")

    # API isteği
    response = httpx.post(
        DEEPGRAM_API_URL,
        params=params,
        headers=headers,
        content=audio_data,
        timeout=300.0,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Deepgram API hatası: {response.status_code} - {response.text[:500]}"
        )

    result = response.json()

    # Transcript çıkar
    transcript = ""
    channels = result.get("results", {}).get("channels", [])
    for channel in channels:
        alternatives = channel.get("alternatives", [])
        for alt in alternatives:
            transcript += alt.get("transcript", "") + " "

    transcript = transcript.strip()
    logger.info(f"Deepgram transkripsiyon tamamlandı: {len(transcript.split())} kelime")

    return transcript

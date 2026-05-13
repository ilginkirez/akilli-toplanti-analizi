"""
benchmark_ami_wer.py
--------------------
AMI Meeting Corpus WER/CER Benchmark
Faster-Whisper (Groq) vs Deepgram Nova-2 karşılaştırması

Kullanım:
  python benchmark_ami_wer.py
"""

import os
import re
import sys
import time
import wave
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
import jiwer
from dotenv import load_dotenv

# Load env variables from root .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Append src to path to import services
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.services.deepgram_transcriber import transcribe_with_deepgram


# ── Paths ────────────────────────────────────────────────────────────────────
XML_DIR = r"C:\Users\merve\Downloads\ami_public_manual_1.6.2\words"
AUDIO_PATH = r"data\ami\audio\ES2016d.Headset-0.wav"
REFERENCE_PATH = r"data\ami\reference\ES2016d_SpeakerA.txt"
LOCAL_PREDICTED_PATH = r"data\ami\results\local_predicted.txt"
DEEPGRAM_PREDICTED_PATH = r"data\ami\results\deepgram_predicted.txt"

# Groq API ayarları
GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = os.getenv("AI_TRANSCRIBE_MODEL", "whisper-large-v3")


def normalize_text(text: str) -> str:
    """Normalize: lowercase, remove punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _extract_audio_chunk(input_path: str, start_sec: float, end_sec: float) -> str:
    """FFmpeg ile ses dosyasından chunk çıkar."""
    temp_fd, temp_path = tempfile.mkstemp(suffix=".flac")
    os.close(temp_fd)
    cmd = [
        "ffmpeg", "-ss", f"{start_sec:.4f}", "-t", f"{end_sec - start_sec:.4f}",
        "-i", input_path, "-vn", "-ar", "16000", "-ac", "1",
        "-c:a", "flac", "-y", temp_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120, check=True)
    return temp_path


def _groq_transcribe_raw(audio_path: str, language: str = "en") -> str:
    """
    Groq Whisper API'ye doğrudan istek at.
    Türkçe normalizer UYGULANMAZ — raw transcript döner.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY tanımlı değil.")

    max_retries = 5
    for attempt in range(max_retries):
        with open(audio_path, "rb") as f:
            response = httpx.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                data={
                    "model": GROQ_MODEL,
                    "language": language,
                    "response_format": "json",
                    "temperature": "0",
                },
                files=[("file", (Path(audio_path).name, f, "audio/flac"))],
                timeout=180.0,
            )

        if response.status_code == 429:
            wait = int(response.headers.get("retry-after", 2 ** attempt * 5))
            print(f"   [Rate Limit] {wait}s bekleniyor (deneme {attempt+1}/{max_retries})...")
            time.sleep(wait)
            continue

        response.raise_for_status()
        return response.json().get("text", "").strip()

    raise RuntimeError("Groq API rate limit aşılamadı.")


def parse_ami_xmls(xml_dir: str, reference_out_path: str, speaker_id: str = None) -> str:
    """AMI XML dosyalarını parse eder, referans metni oluşturur."""
    if not os.path.exists(xml_dir):
        raise FileNotFoundError(f"XML dizini bulunamadı: {xml_dir}")

    if speaker_id:
        files = [f for f in os.listdir(xml_dir)
                 if f.endswith(f".{speaker_id}.words.xml") and f.startswith("ES2016d")]
    else:
        files = [f for f in os.listdir(xml_dir)
                 if f.endswith(".words.xml") and f.startswith("ES2016d")]

    if not files:
        raise FileNotFoundError(f"XML dosyaları {xml_dir} dizininde bulunamadı.")

    word_entries = []
    for file_name in files:
        file_path = os.path.join(xml_dir, file_name)
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            for w in root.iter("w"):
                text = w.text
                if text:
                    start_time_str = w.attrib.get("starttime", "0.0")
                    try:
                        start_time = float(start_time_str)
                    except ValueError:
                        start_time = 0.0
                    word_entries.append((start_time, text))
        except ET.ParseError as e:
            print(f"Hata: {file_name} dosyası parse edilemedi - {e}")
            continue

    if not word_entries:
        print("Uyarı: XML dosyalarından hiçbir kelime çıkarılamadı!")
        return ""

    word_entries.sort(key=lambda x: x[0])
    combined_text = " ".join([w[1] for w in word_entries])
    combined_text = normalize_text(combined_text)

    os.makedirs(os.path.dirname(reference_out_path), exist_ok=True)
    with open(reference_out_path, "w", encoding="utf-8") as f:
        f.write(combined_text)

    return combined_text


def compute_metrics(ref: str, hyp: str) -> dict:
    """WER, CER ve hata dekompozisyonu hesaplar."""
    if not ref or not hyp:
        return {}

    wer_score = jiwer.wer(ref, hyp)
    cer_score = jiwer.cer(ref, hyp)
    measures = jiwer.process_words(ref, hyp)

    ins = measures.insertions
    dels = measures.deletions
    subs = measures.substitutions
    hits = measures.hits
    total_errors = ins + dels + subs

    return {
        "wer": round(wer_score, 4),
        "cer": round(cer_score, 4),
        "insertions": ins,
        "deletions": dels,
        "substitutions": subs,
        "hits": hits,
        "total_errors": total_errors,
        "insertion_ratio": round(ins / total_errors, 4) if total_errors > 0 else 0.0,
        "deletion_ratio": round(dels / total_errors, 4) if total_errors > 0 else 0.0,
        "substitution_ratio": round(subs / total_errors, 4) if total_errors > 0 else 0.0,
        "ref_words": len(ref.split()),
        "hyp_words": len(hyp.split()),
    }


def save_transcript(path: str, text: str):
    """Transcript'i dosyaya kaydeder."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"   Kaydedildi: {path}")


def transcribe_local(audio_path: str, duration: float) -> str:
    """
    Groq Whisper API ile chunk'lar halinde transkripsiyon.
    Türkçe normalizer BYPASS edilir — raw English transcript.
    """
    chunk_size = 600  # 10 dakika
    predicted_parts = []

    for start_sec in range(0, int(duration), chunk_size):
        end_sec = min(start_sec + chunk_size, duration)
        print(f"   Chunk: {start_sec}s - {end_sec:.0f}s ...")

        # Chunk çıkar
        chunk_path = _extract_audio_chunk(audio_path, start_sec, end_sec)
        try:
            text = _groq_transcribe_raw(chunk_path, language="en")
            if text:
                predicted_parts.append(text)
        finally:
            if os.path.exists(chunk_path):
                os.remove(chunk_path)

    return " ".join(predicted_parts)


def transcribe_deepgram(audio_path: str) -> str:
    """Deepgram Nova-2 ile transkripsiyon."""
    return transcribe_with_deepgram(audio_path, language="en")


def print_results(label: str, metrics: dict):
    """Sonuçları formatlı yazdır."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(f"  WER                : {metrics['wer']:.4f}  (%{metrics['wer']*100:.2f})")
    print(f"  CER                : {metrics['cer']:.4f}  (%{metrics['cer']*100:.2f})")
    print(f"-" * 60)
    print(f"  Ref kelime sayısı  : {metrics['ref_words']}")
    print(f"  Hyp kelime sayısı  : {metrics['hyp_words']}")
    print(f"-" * 60)
    print(f"  Insertions         : {metrics['insertions']:>6}  (%{metrics['insertion_ratio']*100:.1f})")
    print(f"  Deletions          : {metrics['deletions']:>6}  (%{metrics['deletion_ratio']*100:.1f})")
    print(f"  Substitutions      : {metrics['substitutions']:>6}  (%{metrics['substitution_ratio']*100:.1f})")
    print(f"  Hits (Doğru)       : {metrics['hits']:>6}")
    print(f"{'=' * 60}")


def print_comparison(local_metrics: dict, deepgram_metrics: dict):
    """İki sistemi yan yana karşılaştır."""
    local_wer_str = f"%{local_metrics['wer']*100:.2f}"
    deep_wer_str = f"%{deepgram_metrics['wer']*100:.2f}"
    local_cer_str = f"%{local_metrics['cer']*100:.2f}"
    deep_cer_str = f"%{deepgram_metrics['cer']*100:.2f}"

    print(f"\n{'=' * 60}")
    print("  KARŞILAŞTIRMA TABLOSU")
    print("=" * 60)
    print(f"  {'Metrik':<20} {'Faster-Whisper':>15} {'Deepgram Nova-2':>15}")
    print(f"  {'-'*50}")
    print(f"  {'WER':<20} {local_wer_str:>15} {deep_wer_str:>15}")
    print(f"  {'CER':<20} {local_cer_str:>15} {deep_cer_str:>15}")
    print(f"  {'Insertions':<20} {local_metrics['insertions']:>15} {deepgram_metrics['insertions']:>15}")
    print(f"  {'Deletions':<20} {local_metrics['deletions']:>15} {deepgram_metrics['deletions']:>15}")
    print(f"  {'Substitutions':<20} {local_metrics['substitutions']:>15} {deepgram_metrics['substitutions']:>15}")
    print(f"  {'Hits':<20} {local_metrics['hits']:>15} {deepgram_metrics['hits']:>15}")
    print(f"  {'Ref Words':<20} {local_metrics['ref_words']:>15} {deepgram_metrics['ref_words']:>15}")
    print(f"  {'Hyp Words':<20} {local_metrics['hyp_words']:>15} {deepgram_metrics['hyp_words']:>15}")
    print(f"  {'-'*50}")

    # Hangi sistem daha iyi?
    if local_metrics["wer"] < deepgram_metrics["wer"]:
        winner = "Faster-Whisper"
        diff = (deepgram_metrics["wer"] - local_metrics["wer"]) * 100
    elif deepgram_metrics["wer"] < local_metrics["wer"]:
        winner = "Deepgram Nova-2"
        diff = (local_metrics["wer"] - deepgram_metrics["wer"]) * 100
    else:
        winner = "Eşit"
        diff = 0.0

    if winner != "Eşit":
        print(f"  KAZANAN (WER)      : {winner} (fark: {diff:.2f} puan)")
    else:
        print("  SONUÇ              : İki sistem eşit WER değerine sahip")

    print(f"{'=' * 60}")


def main():
    print("=" * 60)
    print("  AMI Corpus WER Benchmark")
    print("  Faster-Whisper (Groq) vs Deepgram Nova-2")
    print("=" * 60)

    # ── 1. Referans metin oluştur ────────────────────────────────────────
    print("\n[1/5] XML dosyaları parse ediliyor (Speaker A referansı)...")
    reference_text = parse_ami_xmls(XML_DIR, REFERENCE_PATH, speaker_id="A")
    if not reference_text:
        print("HATA: Boş referans transcript!")
        return
    print(f"   Referans: {len(reference_text.split())} kelime")

    # ── 2. Audio dosyasını kontrol et ────────────────────────────────────
    if not os.path.exists(AUDIO_PATH):
        raise FileNotFoundError(f"Ses dosyası bulunamadı: {AUDIO_PATH}")

    with wave.open(AUDIO_PATH, 'rb') as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        duration = frames / float(rate)
    print(f"   Ses süresi: {duration:.2f} saniye ({duration/60:.1f} dakika)")

    # ── 3. Pipeline A: Whisper Raw (cache varsa oku) ─────────────────────
    if os.path.exists(LOCAL_PREDICTED_PATH):
        print("\n[2/5] Pipeline A: Cache'den okunuyor...")
        with open(LOCAL_PREDICTED_PATH, "r", encoding="utf-8") as f:
            raw_norm = f.read().strip()
        raw_time = 0.0
        print(f"   Cache: {len(raw_norm.split())} kelime")
    else:
        print("\n[2/5] Pipeline A: Whisper Raw transkripsiyon...")
        t0 = time.time()
        raw_text = transcribe_local(AUDIO_PATH, duration)
        raw_time = time.time() - t0
        raw_norm = normalize_text(raw_text)
        save_transcript(LOCAL_PREDICTED_PATH, raw_norm)
        print(f"   Süre: {raw_time:.1f}s | Kelime: {len(raw_norm.split())}")

    local_metrics = compute_metrics(reference_text, raw_norm)

    # ── 4. Deepgram transkripsiyon ───────────────────────────────────────
    print("\n[3/5] Deepgram Nova-2 transkripsiyon yapılıyor...")
    t0 = time.time()
    deepgram_raw = transcribe_deepgram(AUDIO_PATH)
    deepgram_time = time.time() - t0
    deepgram_norm = normalize_text(deepgram_raw)
    save_transcript(DEEPGRAM_PREDICTED_PATH, deepgram_norm)
    print(f"   Süre: {deepgram_time:.1f}s | Kelime: {len(deepgram_norm.split())}")

    deepgram_metrics = compute_metrics(reference_text, deepgram_norm)

    # ── 5. Sonuçları yazdır ──────────────────────────────────────────────
    print("\n[4/5] WER/CER hesaplanıyor...")

    print("\n[5/5] Sonuçlar:")
    print_results("FASTER-WHISPER (Groq Whisper-Large-V3)", local_metrics)
    print_results("DEEPGRAM NOVA-2", deepgram_metrics)
    print_comparison(local_metrics, deepgram_metrics)

    # İşlem süreleri
    print(f"\n  İşlem Süreleri:")
    if raw_time > 0:
        print(f"    Faster-Whisper : {raw_time:.1f} saniye")
    print(f"    Deepgram       : {deepgram_time:.1f} saniye")


if __name__ == "__main__":
    main()

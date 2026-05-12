import os
import re
import sys
import time
import wave
import json
import csv
import tempfile
import subprocess
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
import jiwer
from dotenv import load_dotenv

# Load env variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.services.deepgram_transcriber import transcribe_with_deepgram

# ── Paths ────────────────────────────────────────────────────────────────────
XML_DIR = r"C:\Users\merve\Downloads\ami_public_manual_1.6.2\words"
AUDIO_PATH = r"data\ami\audio\ES2016d.Headset-0.wav"
REFERENCE_PATH = r"data\ami\reference\ES2016d_SpeakerA.txt"

RESULTS_DIR = r"data\benchmark\results"
CSV_OUT = os.path.join(RESULTS_DIR, "asr_comparison.csv")
JSON_OUT = os.path.join(RESULTS_DIR, "asr_comparison.json")

PREDICTED_PATHS = {
    "Faster-Whisper": os.path.join(RESULTS_DIR, "local_predicted.txt"),
    "Deepgram Nova-2": os.path.join(RESULTS_DIR, "deepgram_predicted.txt"),
    "Azure Speech": os.path.join(RESULTS_DIR, "azure_predicted.txt"),
}

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = os.getenv("AI_TRANSCRIBE_MODEL", "whisper-large-v3")


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _extract_audio_chunk(input_path: str, start_sec: float, end_sec: float, fmt="flac") -> str:
    temp_fd, temp_path = tempfile.mkstemp(suffix=f".{fmt}")
    os.close(temp_fd)
    cmd = [
        "ffmpeg", "-ss", f"{start_sec:.4f}", "-t", f"{end_sec - start_sec:.4f}",
        "-i", input_path, "-vn", "-ar", "16000", "-ac", "1",
        "-c:a", "pcm_s16le" if fmt == "wav" else "flac", "-y", temp_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120, check=True)
    return temp_path


def get_audio_duration(path: str) -> float:
    with wave.open(path, 'rb') as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        return frames / float(rate)


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


# ── System Wrappers ──────────────────────────────────────────────────────────

def run_faster_whisper(audio_path: str, duration: float) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY tanımlı değil.")

    chunk_size = 600
    predicted_parts = []

    for start_sec in range(0, int(duration), chunk_size):
        end_sec = min(start_sec + chunk_size, duration)
        chunk_path = _extract_audio_chunk(audio_path, start_sec, end_sec, fmt="flac")
        try:
            max_retries = 5
            success = False
            for attempt in range(max_retries):
                with open(chunk_path, "rb") as f:
                    response = httpx.post(
                        GROQ_API_URL,
                        headers={"Authorization": f"Bearer {api_key}"},
                        data={"model": GROQ_MODEL, "language": "en", "response_format": "json", "temperature": "0"},
                        files=[("file", (Path(chunk_path).name, f, "audio/flac"))],
                        timeout=180.0,
                    )
                if response.status_code == 429:
                    wait = int(response.headers.get("retry-after", 2 ** attempt * 5))
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                predicted_parts.append(response.json().get("text", "").strip())
                success = True
                break
            if not success:
                raise RuntimeError("Groq API rate limit aşılamadı.")
        finally:
            if os.path.exists(chunk_path):
                os.remove(chunk_path)

    return " ".join(predicted_parts)


def run_deepgram(audio_path: str, duration: float) -> str:
    # Deepgram's transcriber accepts the whole file
    return transcribe_with_deepgram(audio_path, language="en")


def run_azure_speech(audio_path: str, duration: float) -> str:
    azure_key = os.getenv("AZURE_SPEECH_KEY")
    azure_region = os.getenv("AZURE_SPEECH_REGION")

    if not azure_key or not azure_region:
        raise ValueError("AZURE_SPEECH_KEY veya AZURE_SPEECH_REGION tanımlı değil. Azure .env ayarlarını kontrol edin.")

    chunk_size = 59  # Azure REST API max 60 seconds
    predicted_parts = []
    
    url = f"https://{azure_region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=en-US"
    headers = {
        "Ocp-Apim-Subscription-Key": azure_key,
        "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
        "Accept": "application/json"
    }

    for start_sec in range(0, int(duration), chunk_size):
        end_sec = min(start_sec + chunk_size, duration)
        chunk_path = _extract_audio_chunk(audio_path, start_sec, end_sec, fmt="wav")
        try:
            with open(chunk_path, "rb") as f:
                audio_data = f.read()
                
            response = httpx.post(url, headers=headers, content=audio_data, timeout=120.0)
            response.raise_for_status()
            
            res_json = response.json()
            if res_json.get("RecognitionStatus") == "Success":
                predicted_parts.append(res_json.get("DisplayText", "").strip())
        finally:
            if os.path.exists(chunk_path):
                os.remove(chunk_path)

    return " ".join(predicted_parts)


# ── Evaluation ───────────────────────────────────────────────────────────────

def evaluate_system(name: str, func, audio_path: str, duration: float, ref_text: str) -> dict:
    result = {
        "model": name,
        "wer": None, "cer": None, 
        "insertions": None, "deletions": None, "substitutions": None, "hits": None,
        "time": None, "rtf": None, "duration": duration,
        "status": "success", "error": None
    }
    
    t0 = time.time()
    try:
        raw_text = func(audio_path, duration)
        proc_time = time.time() - t0
        
        norm_text = normalize_text(raw_text)
        
        # Save transcript
        os.makedirs(RESULTS_DIR, exist_ok=True)
        with open(PREDICTED_PATHS[name], "w", encoding="utf-8") as f:
            f.write(norm_text)
            
        # Calculate metrics
        measures = jiwer.process_words(ref_text, norm_text)
        
        result["wer"] = round(jiwer.wer(ref_text, norm_text), 4)
        result["cer"] = round(jiwer.cer(ref_text, norm_text), 4)
        result["insertions"] = measures.insertions
        result["deletions"] = measures.deletions
        result["substitutions"] = measures.substitutions
        result["hits"] = measures.hits
        result["time"] = round(proc_time, 2)
        result["rtf"] = round(proc_time / duration, 4) if duration > 0 else 0
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"HATA ({name}): {e}")
        traceback.print_exc()
        
    return result


def main():
    print("=" * 80)
    print("  ASR Benchmark Karşılaştırması")
    print("  Faster-Whisper vs Deepgram Nova-2 vs Azure Speech")
    print("=" * 80)
    
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("\n[1/5] XML dosyaları parse ediliyor (Speaker A referansı)...")
    try:
        ref_text = parse_ami_xmls(XML_DIR, REFERENCE_PATH, speaker_id="A")
        if not ref_text:
            print("HATA: Boş referans transcript!")
            return
    except Exception as e:
        print(f"Referans oluşturulurken hata: {e}")
        return
        
    if not os.path.exists(AUDIO_PATH):
        print(f"Ses dosyası bulunamadı: {AUDIO_PATH}")
        return
        
    duration = get_audio_duration(AUDIO_PATH)
    print(f"Ses Süresi: {duration:.2f} saniye")
    
    systems = [
        ("Faster-Whisper", run_faster_whisper),
        ("Deepgram Nova-2", run_deepgram),
        ("Azure Speech", run_azure_speech),
    ]
    
    results = []
    
    for name, func in systems:
        print(f"\n[{name}] Çalıştırılıyor...")
        res = evaluate_system(name, func, AUDIO_PATH, duration, ref_text)
        results.append(res)
        
    # ── Output Table ─────────────────────────────────────────────────────────
    
    print("\n" + "=" * 90)
    print(f"{'Model':<18} | {'WER':<6} | {'CER':<6} | {'Insertions':<10} | {'Deletions':<9} | {'Substitutions':<13} | {'Hits':<6} | {'Time':<6} | {'RTF':<6}")
    print("-" * 90)
    
    valid_results = []
    
    for r in results:
        m = r["model"]
        if r["status"] == "error":
            print(f"{m:<18} | {'HATA':<6} | {'-':<6} | {'-':<10} | {'-':<9} | {'-':<13} | {'-':<6} | {'-':<6} | {'-':<6}")
        else:
            valid_results.append(r)
            print(f"{m:<18} | {r['wer']:<6.4f} | {r['cer']:<6.4f} | {r['insertions']:<10} | {r['deletions']:<9} | {r['substitutions']:<13} | {r['hits']:<6} | {r['time']:<6.2f} | {r['rtf']:<6.4f}")
            
    print("=" * 90)
    
    # ── Best Model Determination ─────────────────────────────────────────────
    
    if valid_results:
        best_wer_model = min(valid_results, key=lambda x: x["wer"])
        best_cer_model = min(valid_results, key=lambda x: x["cer"])
        best_rtf_model = min(valid_results, key=lambda x: x["rtf"])
        
        print("\nSonuç Yorumu:")
        print(f"* WER açısından en iyi model: {best_wer_model['model']} (WER: {best_wer_model['wer']})")
        print(f"* CER açısından en iyi model: {best_cer_model['model']} (CER: {best_cer_model['cer']})")
        print(f"* Hız açısından en iyi model: {best_rtf_model['model']} (RTF: {best_rtf_model['rtf']})")
        
        # Local vs Commercial comparison
        local_model = next((r for r in valid_results if r["model"] == "Faster-Whisper"), None)
        commercial_models = [r for r in valid_results if r["model"] in ("Deepgram Nova-2", "Azure Speech")]
        
        if local_model and commercial_models:
            best_commercial = min(commercial_models, key=lambda x: x["wer"])
            diff = abs(local_model["wer"] - best_commercial["wer"]) * 100
            
            better_one = "Local sistem (Faster-Whisper)" if local_model["wer"] < best_commercial["wer"] else f"Ticari sistem ({best_commercial['model']})"
            print(f"* Local sistem ile en iyi ticari sistem arasındaki WER farkı: {diff:.2f} puan ({better_one} daha iyi)")
            
    # ── Save Results ─────────────────────────────────────────────────────────
    
    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    with open(CSV_OUT, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Model", "Status", "WER", "CER", "Insertions", "Deletions", "Substitutions", "Hits", "Time", "RTF", "Error"])
        for r in results:
            writer.writerow([
                r["model"], r["status"], r.get("wer", ""), r.get("cer", ""),
                r.get("insertions", ""), r.get("deletions", ""), r.get("substitutions", ""),
                r.get("hits", ""), r.get("time", ""), r.get("rtf", ""), r.get("error", "")
            ])
            
    print(f"\nDosyalar kaydedildi:")
    print(f" - {JSON_OUT}")
    print(f" - {CSV_OUT}")
    for k, v in PREDICTED_PATHS.items():
        if os.path.exists(v):
            print(f" - {v} ({k})")

if __name__ == "__main__":
    main()

import os
import random
import re
import sys
import time
import wave
import tempfile
import subprocess
import xml.etree.ElementTree as ET
import httpx
import jiwer
import azure.cognitiveservices.speech as speechsdk
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, "..", ".env"))

sys.path.append(os.path.join(BASE_DIR, "src"))
from src.services.deepgram_transcriber import transcribe_with_deepgram

XML_DIR = r"C:\Users\merve\Downloads\ami_public_manual_1.6.2\words"
AUDIO_DIR = os.path.join(BASE_DIR, "data", "ami", "audio")

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = os.getenv("AI_TRANSCRIBE_MODEL", "whisper-large-v3")

AZURE_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION", "swedencentral")

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_ami_xml(xml_path: str) -> str:
    if not os.path.exists(xml_path):
        return ""
    word_entries = []
    try:
        tree = ET.parse(xml_path)
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
    except Exception as e:
        print(f"XML Parse Error: {e}")
        return ""

    if not word_entries:
        return ""
    word_entries.sort(key=lambda x: x[0])
    combined_text = " ".join([w[1] for w in word_entries])
    return normalize_text(combined_text)

def _extract_audio_chunk(input_path: str, start_sec: float, end_sec: float) -> str:
    temp_fd, temp_path = tempfile.mkstemp(suffix=".flac")
    os.close(temp_fd)
    cmd = [
        "ffmpeg", "-ss", f"{start_sec:.4f}", "-t", f"{end_sec - start_sec:.4f}",
        "-i", input_path, "-vn", "-ar", "16000", "-ac", "1",
        "-c:a", "flac", "-y", temp_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120, check=True)
    return temp_path

def transcribe_whisper(audio_path: str, duration: float) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return ""

    chunk_size = 600
    predicted_parts = []
    for start_sec in range(0, int(duration), chunk_size):
        end_sec = min(start_sec + chunk_size, duration)
        chunk_path = _extract_audio_chunk(audio_path, start_sec, end_sec)
        try:
            with open(chunk_path, "rb") as f:
                response = httpx.post(
                    GROQ_API_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                    data={"model": GROQ_MODEL, "language": "en", "response_format": "json", "temperature": "0"},
                    files=[("file", (Path(chunk_path).name, f, "audio/flac"))],
                    timeout=180.0,
                )
            if response.status_code == 200:
                text = response.json().get("text", "").strip()
                if text:
                    predicted_parts.append(text)
        except Exception:
            pass
        finally:
            if os.path.exists(chunk_path):
                os.remove(chunk_path)
    return normalize_text(" ".join(predicted_parts))

def transcribe_deepgram_local(audio_path: str) -> str:
    try:
        raw = transcribe_with_deepgram(audio_path, language="en")
        return normalize_text(raw)
    except Exception as e:
        return ""

def transcribe_azure(audio_path: str, duration: float) -> str:
    if not AZURE_KEY:
        return ""

    temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
    os.close(temp_fd)
    subprocess.run([
        "ffmpeg", "-y", "-i", audio_path, "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", temp_path
    ], capture_output=True, check=True)

    try:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        speech_config.speech_recognition_language = "en-US"
        audio_config = speechsdk.audio.AudioConfig(filename=temp_path)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        done = False
        recognized_texts = []

        def stop_cb(evt):
            nonlocal done
            done = True

        def recognized_cb(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                text = evt.result.text.strip()
                if text:
                    recognized_texts.append(text)
            
        speech_recognizer.recognized.connect(recognized_cb)
        speech_recognizer.session_stopped.connect(stop_cb)
        speech_recognizer.canceled.connect(stop_cb)

        speech_recognizer.start_continuous_recognition()
        while not done:
            time.sleep(0.5)
        speech_recognizer.stop_continuous_recognition()

        return normalize_text(" ".join(recognized_texts))
    except Exception as e:
        return ""
    finally:
        try:
            del speech_recognizer
            del audio_config
        except NameError:
            pass
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

def main():
    wav_files = []
    for root, _, files in os.walk(AUDIO_DIR):
        for f in files:
            if f.endswith(".wav"):
                wav_files.append(os.path.join(root, f))
                
    if not wav_files:
        print(f"HATA: {AUDIO_DIR} icerisinde .wav dosyasi bulunamadi.")
        return

    mapping = {"0": "A", "1": "B", "2": "C", "3": "D", "4": "E"}
    
    audio_path = None
    while True:
        if not wav_files:
            print("Uygun ses dosyasi / XML ikilisi bulunamadi.")
            return
            
        audio_path_candidate = random.choice(wav_files)
        audio_file = os.path.basename(audio_path_candidate)
        match = re.match(r"(.+)\.Headset-(\d+)\.wav", audio_file)
        if match:
            meeting_id = match.group(1)
            speaker_idx = match.group(2)
            speaker_id = mapping.get(speaker_idx, "A")
            xml_path = os.path.join(XML_DIR, f"{meeting_id}.{speaker_id}.words.xml")
            
            ref_text = parse_ami_xml(xml_path)
            if ref_text and len(ref_text.split()) > 10:
                audio_path = audio_path_candidate
                break
        
        wav_files.remove(audio_path_candidate)

    print(f"\n=============================================")
    print(f"Secilen Dosya : {audio_file}")
    print(f"Meeting ID    : {meeting_id}, Speaker ID: {speaker_id}")
    print(f"=============================================")
    
    with wave.open(audio_path, 'rb') as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        orig_duration = frames / float(rate)
        
    test_duration = min(orig_duration, 300.0)
    
    temp_fd, temp_audio_path = tempfile.mkstemp(suffix=".wav")
    os.close(temp_fd)
    subprocess.run([
        "ffmpeg", "-y", "-i", audio_path, "-ss", "0", "-t", str(test_duration),
        "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", temp_audio_path
    ], capture_output=True, check=True)
    
    ref_word_entries = []
    if os.path.exists(xml_path):
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for w in root.iter("w"):
            text = w.text
            if text:
                try:
                    start_time = float(w.attrib.get("starttime", "0.0"))
                except ValueError:
                    start_time = 0.0
                if start_time <= test_duration:
                    ref_word_entries.append((start_time, text))
    ref_word_entries.sort(key=lambda x: x[0])
    ref_text = normalize_text(" ".join([w[1] for w in ref_word_entries]))
    
    print(f"Referans Kelime : {len(ref_text.split())} (ilk {test_duration} sn)")
    print(f"Ses Suresi      : {test_duration:.2f} saniye")
    print("-" * 45)
    
    print(">> Whisper (Groq) transkripsiyonu basladi...")
    t0 = time.time()
    hyp_whisper = transcribe_whisper(temp_audio_path, test_duration)
    whisper_time = time.time() - t0
    
    print(">> Deepgram transkripsiyonu basladi...")
    t0 = time.time()
    hyp_deepgram = transcribe_deepgram_local(temp_audio_path)
    deepgram_time = time.time() - t0
    
    print(">> Azure transkripsiyonu basladi...")
    t0 = time.time()
    hyp_azure = transcribe_azure(temp_audio_path, test_duration)
    azure_time = time.time() - t0
    
    os.remove(temp_audio_path)
    
    metrics = {}
    for name, hyp, t in [("Whisper", hyp_whisper, whisper_time), 
                         ("Deepgram", hyp_deepgram, deepgram_time), 
                         ("Azure", hyp_azure, azure_time)]:
        if hyp:
            wer = jiwer.wer(ref_text, hyp)
            cer = jiwer.cer(ref_text, hyp)
        else:
            wer, cer = 1.0, 1.0
            
        metrics[name] = {"wer": wer, "cer": cer, "time": t}
    
    print("\n" + "="*60)
    print("  WER / CER ANALIZ SONUCLARI")
    print("="*60)
    for name, m in metrics.items():
        print(f"  {name:15} | WER: {m['wer']:.4f} (%{m['wer']*100:.1f}) | CER: {m['cer']:.4f} | Sure: {m['time']:.2f}s")
    print("="*60)

if __name__ == '__main__':
    main()

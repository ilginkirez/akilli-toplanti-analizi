import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import jiwer
from dotenv import load_dotenv

# Load env variables from root .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Append src to path to import services
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from services.ai_transcription import transcribe_audio_clip_text
import wave

def parse_ami_xmls(xml_dir: str, reference_out_path: str, speaker_id: str = None):
    """
    Parses AMI words XML files, extracts words, sorts by time, and writes to a text file.
    """
    if not os.path.exists(xml_dir):
        raise FileNotFoundError(f"XML dizini bulunamadi: {xml_dir}")

    if speaker_id:
        files = [f for f in os.listdir(xml_dir) if f.endswith(f".{speaker_id}.words.xml") and f.startswith("ES2016d")]
    else:
        files = [f for f in os.listdir(xml_dir) if f.endswith(".words.xml") and f.startswith("ES2016d")]
        
    if not files:
        raise FileNotFoundError(f"XML dosyalari {xml_dir} dizininde bulunamadi.")

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
            print(f"Hata: {file_name} dosyasi parse edilemedi - {e}")
            continue

    if not word_entries:
        print("Uyari: XML dosyalarindan hicbir kelime cikarilamadi!")
        return ""

    # Sort by starttime
    word_entries.sort(key=lambda x: x[0])
    
    # Combine text
    combined_text = " ".join([w[1] for w in word_entries])
    
    # Normalize
    combined_text = combined_text.lower()
    combined_text = re.sub(r'[^\w\s]', '', combined_text)
    combined_text = re.sub(r'\s+', ' ', combined_text).strip()
    
    # Save to file
    os.makedirs(os.path.dirname(reference_out_path), exist_ok=True)
    with open(reference_out_path, "w", encoding="utf-8") as f:
        f.write(combined_text)
        
    return combined_text

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def main():
    # Paths
    xml_dir = r"C:\Users\merve\Downloads\ami_public_manual_1.6.2\words"
    audio_path = r"data\ami\audio\ES2016d.Headset-0.wav"
    reference_path = r"data\ami\reference\ES2016d_SpeakerA.txt"
    results_path = r"data\ami\results\ES2016d_SpeakerA_predicted.txt"

    # 1. Parse XML and Generate Reference (Sadece Speaker A)
    print("1. XML dosyalari parse ediliyor (Sadece Konusmaci A)...")
    reference_text = parse_ami_xmls(xml_dir, reference_path, speaker_id="A")
    if not reference_text:
        print("Uyari: Bos referans transcript olustu.")

    # 2. Check Audio File
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Ses dosyasi bulunamadi: {audio_path}")

    # 3. Get audio duration and transcribe in chunks
    print("2. Ses dosyasi transcriber ile isleniyor (10 dakikalik parcalar halinde)...")
    try:
        # wav dosyasinin suresini bul
        with wave.open(audio_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            
        print(f"   Ses dosyasi suresi: {duration:.2f} saniye")
        
        chunk_size = 600  # 10 dakika (saniye)
        predicted_parts = []
        
        for start_sec in range(0, int(duration), chunk_size):
            end_sec = min(start_sec + chunk_size, duration)
            print(f"   Islemiyor: {start_sec} - {end_sec:.2f} saniye arasi...")
            
            text = transcribe_audio_clip_text(
                audio_path, 
                start_sec=start_sec, 
                end_sec=end_sec, 
                language="en"
            )
            if text:
                predicted_parts.append(text)
                
        predicted_text = " ".join(predicted_parts)
        
    except Exception as e:
        print(f"Hata: Transcription basarisiz oldu: {e}")
        return

    if not predicted_text:
        print("Uyari: Transkripsiyon sonucu bos.")

    # 4. Save predicted text
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        f.write(predicted_text)

    # 5. Normalize and Benchmark
    print("3. WER ve CER hesaplaniyor...")
    predicted_norm = normalize_text(predicted_text)
    
    if not reference_text:
        print("Referans metin bos oldugu icin hesaplama yapilamadi.")
        return
        
    if not predicted_norm:
        print("Tahmin edilen metin bos oldugu icin hesaplama yapilamadi (Error rate %100 kabul edilebilir).")
        return

    # Calculate word counts
    ref_word_count = len(reference_text.split())
    pred_word_count = len(predicted_norm.split())

    # jiwer calculations
    wer = jiwer.wer(reference_text, predicted_norm)
    cer = jiwer.cer(reference_text, predicted_norm)

    print("\n---------------------------------------")
    print("BENCHMARK SONUCLARI")
    print("---------------------------------------")
    print(f"Reference word count : {ref_word_count}")
    print(f"Predicted word count : {pred_word_count}")
    print(f"WER                  : {wer:.4f}")
    print(f"WER %                : {wer * 100:.2f}%")
    print(f"CER                  : {cer:.4f}")
    print(f"CER %                : {cer * 100:.2f}%")
    print("---------------------------------------")

if __name__ == "__main__":
    main()

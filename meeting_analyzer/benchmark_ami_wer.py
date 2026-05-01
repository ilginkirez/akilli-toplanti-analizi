"""
benchmark_ami_wer.py
--------------------
AMI Meeting Corpus WER/cpWER Benchmark (v2 — He & Whitehill 2025 uyumlu)

Ozellikler:
  - Standard WER (tek konusmaci referansi)
  - cpWER (concatenated minimum-permutation WER — tum konusmacilarin
    referanslarinin en uygun sirada birlestirilerek hesaplanmasi)
  - Hata Dekompozisyonu (Insertion/Deletion/Substitution)
  - He & Whitehill Tablo II referans degerleri ile kiyaslama

Kullanim:
  python benchmark_ami_wer.py
"""

import itertools
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


# ── He & Whitehill (2025) Tablo II Referans Degerleri ──────────────────────
HE_WHITEHILL_REF = {
    "AMI-SDM eval cpWER araliği": "21.2 — 24.9",
    "AMI-IHM eval cpWER araliği": "14.9 — 28.4",
}


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


def parse_ami_xmls_per_speaker(xml_dir: str, meeting_prefix: str = "ES2016d"):
    """
    AMI XML dosyalarindan her konusmaci icin ayri referans metni cikar.
    
    Returns: dict[str, str] — { "A": "metin...", "B": "metin...", ... }
    """
    files = [f for f in os.listdir(xml_dir) if f.endswith(".words.xml") and f.startswith(meeting_prefix)]
    
    speaker_texts = {}
    for file_name in files:
        # Dosya adi formati: ES2016d.X.words.xml (X = konusmaci ID)
        parts = file_name.replace(".words.xml", "").split(".")
        if len(parts) >= 2:
            speaker_id = parts[-1]  # Son kisim konusmaci ID
        else:
            continue
            
        file_path = os.path.join(xml_dir, file_name)
        word_entries = []
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
        except ET.ParseError:
            continue
            
        if word_entries:
            word_entries.sort(key=lambda x: x[0])
            combined = " ".join([w[1] for w in word_entries])
            combined = normalize_text(combined)
            speaker_texts[speaker_id] = combined
    
    return speaker_texts


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def compute_error_decomposition(ref: str, hyp: str) -> dict:
    """
    WER, CER ve hata dekompozisyonu (Ins/Del/Sub) hesaplar.
    He & Whitehill (2025) Tablo II ile kiyaslanabilir metrikler uretir.
    """
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


def compute_cpwer(speaker_refs: dict, hypothesis: str) -> dict:
    """
    Concatenated minimum-Permutation Word Error Rate (cpWER).
    
    Tum konusmaci referanslarinin tum permutasyonlarini deneyerek
    en dusuk WER'i veren siralama ile hesaplar.
    
    Bu yaklasim He & Whitehill (2025) Tablo II'deki cpWER metrigine
    tekabul eder.
    
    Args:
        speaker_refs: { "A": "ref metin", "B": "ref metin", ... }
        hypothesis:   Whisper'in tek kanal transkripsiyon ciktisi
    
    Returns:
        dict: cpWER sonuclari + en iyi permutasyon bilgisi
    """
    if not speaker_refs or not hypothesis:
        return {}
    
    hyp_norm = normalize_text(hypothesis)
    speaker_ids = list(speaker_refs.keys())
    ref_texts = [speaker_refs[sid] for sid in speaker_ids]
    
    best_wer = float("inf")
    best_perm = None
    best_concat_ref = None
    
    # Tum permutasyonlari dene (konusmaci sayisi genelde 4-5, maliyet dusuk)
    for perm in itertools.permutations(range(len(ref_texts))):
        concat_ref = " ".join(ref_texts[i] for i in perm)
        w = jiwer.wer(concat_ref, hyp_norm)
        if w < best_wer:
            best_wer = w
            best_perm = tuple(speaker_ids[i] for i in perm)
            best_concat_ref = concat_ref
    
    # En iyi permutasyonla tam dekompozisyon
    result = compute_error_decomposition(best_concat_ref, hyp_norm)
    result["cpwer"] = round(best_wer, 4)
    result["best_permutation"] = list(best_perm) if best_perm else []
    result["n_permutations_tested"] = len(list(itertools.permutations(range(len(ref_texts)))))
    
    return result


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

    # 1b. Tum konusmacilari parse et (cpWER icin)
    print("1b. Tum konusmaci referanslari parse ediliyor (cpWER icin)...")
    all_speaker_refs = parse_ami_xmls_per_speaker(xml_dir)
    if all_speaker_refs:
        print(f"    Bulunan konusmacilar: {list(all_speaker_refs.keys())}")
        for sid, txt in all_speaker_refs.items():
            print(f"      {sid}: {len(txt.split())} kelime")

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

    # 5. Standard WER (Sadece Speaker A referansi)
    print("\n3. STANDARD WER hesaplaniyor (Sadece Konusmaci A)...")
    predicted_norm = normalize_text(predicted_text)
    
    if reference_text and predicted_norm:
        std_results = compute_error_decomposition(reference_text, predicted_norm)
        
        print("\n" + "=" * 70)
        print(" STANDARD WER SONUCLARI (Tek Konusmaci Referansi)")
        print("=" * 70)
        print(f"  Referans kelime sayisi  : {std_results['ref_words']}")
        print(f"  Tahmin kelime sayisi    : {std_results['hyp_words']}")
        print(f"  WER                     : {std_results['wer']:.4f} (%{std_results['wer']*100:.2f})")
        print(f"  CER                     : {std_results['cer']:.4f} (%{std_results['cer']*100:.2f})")
        print("-" * 70)
        print(f"  Insertions              : {std_results['insertions']:>6}  (%{std_results['insertion_ratio']*100:.1f})")
        print(f"  Deletions               : {std_results['deletions']:>6}  (%{std_results['deletion_ratio']*100:.1f})")
        print(f"  Substitutions           : {std_results['substitutions']:>6}  (%{std_results['substitution_ratio']*100:.1f})")
        print(f"  Hits (Dogru)            : {std_results['hits']:>6}")
        print("=" * 70)
        
        if std_results["insertion_ratio"] > 0.60:
            print("  [!] YUKSEK INSERTION: Diger konusmacilarin sesi leakage olarak algilaniyor.")
        
    # 6. cpWER (Tum konusmaci referanslari)
    if all_speaker_refs and predicted_norm:
        print("\n4. cpWER hesaplaniyor (Tum konusmaci referanslari)...")
        cpwer_results = compute_cpwer(all_speaker_refs, predicted_text)
        
        if cpwer_results:
            print("\n" + "=" * 70)
            print(" cpWER SONUCLARI (Concatenated min-Permutation WER)")
            print("=" * 70)
            print(f"  cpWER                   : {cpwer_results['cpwer']:.4f} (%{cpwer_results['cpwer']*100:.2f})")
            print(f"  Test edilen permutasyon : {cpwer_results['n_permutations_tested']}")
            print(f"  En iyi siralama         : {' -> '.join(cpwer_results['best_permutation'])}")
            print("-" * 70)
            print(f"  Insertions              : {cpwer_results['insertions']:>6}  (%{cpwer_results['insertion_ratio']*100:.1f})")
            print(f"  Deletions               : {cpwer_results['deletions']:>6}  (%{cpwer_results['deletion_ratio']*100:.1f})")
            print(f"  Substitutions           : {cpwer_results['substitutions']:>6}  (%{cpwer_results['substitution_ratio']*100:.1f})")
            print("=" * 70)
    
    # 7. He & Whitehill Referans Kiyaslamasi
    print("\n" + "=" * 70)
    print(" He & Whitehill (2025) TABLO II REFERANS KIYASLAMASI")
    print("=" * 70)
    for label, val in HE_WHITEHILL_REF.items():
        print(f"  {label}: {val}")
    print("-" * 70)
    
    if reference_text and predicted_norm:
        our_wer = std_results['wer'] * 100
        print(f"  Bizim Standard WER (SDM, tek ref) : %{our_wer:.2f}")
        print(f"  NOT: Standard WER, cpWER'den yuksektir cunku diger")
        print(f"       konusmacilarin metinleri insertion hatasi olarak sayilir.")
    
    if all_speaker_refs and predicted_norm and cpwer_results:
        our_cpwer = cpwer_results['cpwer'] * 100
        print(f"  Bizim cpWER (SDM, tum ref)        : %{our_cpwer:.2f}")
        if our_cpwer <= 24.9:
            print(f"  [OK] AMI-SDM referans araliginda (21.2-24.9)")
        elif our_cpwer <= 30.0:
            print(f"  [~] AMI-SDM referans araligina yakin")
        else:
            print(f"  [!] AMI-SDM referans araliginin uzerinde")
    
    print("=" * 70)

if __name__ == "__main__":
    main()

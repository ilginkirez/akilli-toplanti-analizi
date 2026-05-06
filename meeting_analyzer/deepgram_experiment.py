"""
deepgram_experiment.py
----------------------
Deepgram (nova-2) modeli ile mevcut STT sistemimizin performansini kiyaslar.
Merve ve Ilgin'in izole kanallarini Deepgram API'sine gonderir ve 
normalizasyon uygulanmis sekilde WER/CER olcumu yapar.
"""

import json
import os
import sys
import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jiwer
from src.services.turkish_normalizer import normalize_for_wer

DEEPGRAM_API_KEY = "ef358f254a425705b8f4d947e1ad6fb44d665d22"
DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

def transcribe_with_deepgram(audio_path: str) -> str:
    """Ses dosyasini Deepgram API'sine gonderip donen metni alir."""
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/ogg" # OGG Vorbis
    }
    params = {
        "language": "tr",
        "model": "nova-2",
        "smart_format": "false",
        "punctuate": "false"
    }
    
    with open(audio_path, "rb") as audio_file:
        audio_data = audio_file.read()
        
    print(f"  -> Deepgram'a gonderiliyor: {os.path.basename(audio_path)}")
    response = httpx.post(
        DEEPGRAM_URL, 
        headers=headers, 
        params=params, 
        content=audio_data, 
        timeout=120.0
    )
    
    if response.status_code != 200:
        print(f"  [HATA] Deepgram API Hatasi: {response.status_code} - {response.text}")
        return ""
        
    data = response.json()
    try:
        transcript = data["results"]["channels"][0]["alternatives"][0]["transcript"]
        return transcript
    except KeyError:
        print("  [HATA] Deepgram yanitinda transcript bulunamadi.")
        return ""

def compute_wer_detailed(ref: str, hyp: str) -> dict:
    if not ref or not hyp:
        return {"wer": 1.0, "cer": 1.0, "ins": 0, "del": 0, "sub": 0, "hits": 0}
    w = jiwer.process_words(ref, hyp)
    total = w.insertions + w.deletions + w.substitutions
    return {
        "wer": round(jiwer.wer(ref, hyp), 4),
        "cer": round(jiwer.cer(ref, hyp), 4),
        "ins": w.insertions,
        "del": w.deletions,
        "sub": w.substitutions,
        "hits": w.hits,
    }

def run_deepgram_experiment():
    MEETING_DIR = r"c:\Users\HP\Desktop\akilli-toplanti-analizi\meeting_analyzer\recordings\meet-m-62478a64"
    
    ref_map = {
        "Merve": {
            "audio": os.path.join(MEETING_DIR, "individual", "par_934e83-TR_AMxYSJLVPzLgrZ.ogg"),
            "ref": os.path.join(MEETING_DIR, "ground_truth", "ref_merve.txt")
        },
        "Ilgın": {
            "audio": os.path.join(MEETING_DIR, "individual", "par_cfd4ec-TR_AMipWn59xVZVBS.ogg"),
            "ref": os.path.join(MEETING_DIR, "ground_truth", "ref_ilgin.txt")
        }
    }
    
    print("======================================================================")
    print(" DEEPGRAM (nova-2) vs BIZIM SISTEM (Whisper Large-v3) KIYASLAMASI")
    print("======================================================================")
    
    all_wer = []
    all_cer = []
    
    for speaker, paths in ref_map.items():
        with open(paths["ref"], "r", encoding="utf-8") as f:
            ref_raw = f.read().strip()
            
        hyp_raw = transcribe_with_deepgram(paths["audio"])
        
        # WER adil karsilastirmasi icin ayni normalizasyonu (lowercase, noktalama kaldirma) yapiyoruz
        ref_norm = normalize_for_wer(ref_raw)
        hyp_norm = normalize_for_wer(hyp_raw)
        
        metrics = compute_wer_detailed(ref_norm, hyp_norm)
        
        all_wer.append(metrics["wer"])
        all_cer.append(metrics["cer"])
        
        print(f"\n  KONUSMACI: {speaker}")
        print("-" * 50)
        print(f"  WER  : %{metrics['wer']*100:.2f}")
        print(f"  CER  : %{metrics['cer']*100:.2f}")
        print(f"  Hata : Ins={metrics['ins']}, Del={metrics['del']}, Sub={metrics['sub']}")
        print(f"  Dogru: {metrics['hits']} kelime")
        print("-" * 50)
        
    avg_wer = sum(all_wer) / len(all_wer)
    avg_cer = sum(all_cer) / len(all_cer)
    
    print("\n======================================================================")
    print(" DEEPGRAM ORTALAMA SONUCLAR")
    print("======================================================================")
    print(f"  Ortalama WER : %{avg_wer*100:.2f}")
    print(f"  Ortalama CER : %{avg_cer*100:.2f}")
    print("======================================================================")

if __name__ == "__main__":
    run_deepgram_experiment()

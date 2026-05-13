# -*- coding: utf-8 -*-
"""
ami_randomsearch_azure.py
-------------------------
AMI Meeting Corpus üzerinde Azure Speech STT için RandomSearch
hiperparametre optimizasyonu ve WER/CER analizi.

HuggingFace'teki DLL sorunlarını (torchcodec vb.) ve WinError 10038'i 
aşmak için lokaldeki AMI audio dosyasını ve XML'leri kullanır.
"""

import os
import re
import sys
import json
import csv
import time
import tempfile
import subprocess
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx
import jiwer
import numpy as np
import soundfile as sf
from dotenv import load_dotenv
from sklearn.model_selection import ParameterSampler

# ── Env yükle ────────────────────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

AZURE_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION", "swedencentral")

# ── Dosya Yolları ───────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BASE_DIR, "data", "benchmark", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Lokal dosyalar
LOCAL_AUDIO = os.path.join(BASE_DIR, "data", "ami", "audio", "ES2016d.Headset-0.wav")
LOCAL_XML_DIR = r"C:\Users\merve\Downloads\ami_public_manual_1.6.2\words"
MEETING_ID = "ES2016d"
SPEAKER_ID = "A"

# ── Sabitler ─────────────────────────────────────────────────────────────────
N_SEARCH_SAMPLES = 5       # RandomSearch'te kullanılacak örnek sayısı
N_RANDOM_CONFIGS = 15      # Denenecek rastgele konfigürasyon sayısı
N_FINAL_SAMPLES  = 20      # Final değerlendirmede kullanılacak örnek sayısı
RANDOM_SEED      = 42


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_chunk(input_path: str, start_sec: float, end_sec: float) -> str:
    temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
    os.close(temp_fd)
    # Başına ve sonuna yarım saniye padding ekle (kelimelerin kesilmemesi için)
    s = max(0, start_sec - 0.5)
    e = end_sec + 0.5
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{s:.4f}",
        "-t", f"{e - s:.4f}",
        "-i", input_path,
        "-vn", "-ar", "16000", "-ac", "1",
        "-c:a", "pcm_s16le",
        temp_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=120, check=True)
    return temp_path

def get_wav_duration(path: str) -> float:
    info = sf.info(path)
    return info.duration


# =============================================================================
# LOKAL VERİ HAZIRLAMA (XML Parse)
# =============================================================================

def load_local_ami_samples(n_samples: int) -> list:
    """
    Lokal XML'leri tarayarak uzunluğu uygun (örn. > 3 sn) anlamlı cümle 
    parçacıkları oluşturur ve bunları audio'dan extract eder.
    """
    xml_file = os.path.join(LOCAL_XML_DIR, f"{MEETING_ID}.{SPEAKER_ID}.words.xml")
    if not os.path.exists(xml_file):
        raise FileNotFoundError(f"XML dosyası bulunamadı: {xml_file}")
    if not os.path.exists(LOCAL_AUDIO):
        raise FileNotFoundError(f"Audio dosyası bulunamadı: {LOCAL_AUDIO}")

    print(f"\n  Lokal XML parse ediliyor: {xml_file}")
    
    words = []
    tree = ET.parse(xml_file)
    root = tree.getroot()
    for w in root.iter("w"):
        text = w.text
        if text:
            start = float(w.attrib.get("starttime", -1.0))
            end = float(w.attrib.get("endtime", start))
            if start >= 0:
                words.append((start, end, text))

    words.sort(key=lambda x: x[0])

    # Kelimeleri "cümle" chunk'larına ayır (arada 1 sn den fazla boşluk varsa böl)
    chunks = []
    current_chunk = []
    
    for i, (w_s, w_e, text) in enumerate(words):
        if not current_chunk:
            current_chunk = [(w_s, w_e, text)]
        else:
            prev_end = current_chunk[-1][1]
            if w_s - prev_end > 1.5:  # 1.5 saniye boşluk = yeni chunk
                chunks.append(current_chunk)
                current_chunk = [(w_s, w_e, text)]
            else:
                current_chunk.append((w_s, w_e, text))
    if current_chunk:
        chunks.append(current_chunk)

    # Uygun uzunluktaki chunk'ları seç (en az 3 sn, en fazla 20 sn)
    valid_chunks = []
    for c in chunks:
        start_t = c[0][0]
        end_t = c[-1][1]
        dur = end_t - start_t
        if 3.0 <= dur <= 20.0 and len(c) >= 5:
            text_str = " ".join([w[2] for w in c])
            # Sadece alfanumerik metinleri kabul et
            if re.search('[a-zA-Z]', text_str):
                valid_chunks.append({
                    "start": start_t,
                    "end": end_t,
                    "duration": dur,
                    "text": text_str
                })

    temp_dir = os.path.join(RESULTS_DIR, "ami_audio_cache")
    os.makedirs(temp_dir, exist_ok=True)

    samples = []
    count = 0
    # İlk n_samples tanesini al (Biraz rastgelelik için atlayarak da alabiliriz ama sıralı alalım)
    # Daha fazla çeşitlilik için adım boyu:
    step = max(1, len(valid_chunks) // n_samples)
    
    for i in range(0, len(valid_chunks), step):
        if count >= n_samples:
            break
            
        vc = valid_chunks[i]
        sample_id = f"ami_local_{count:03d}"
        audio_path = os.path.join(temp_dir, f"{sample_id}.wav")
        
        if not os.path.exists(audio_path):
            extract_chunk(LOCAL_AUDIO, vc["start"], vc["end"])
            # FFmpeg extract_chunk was already doing temp file logic, let's rename it
            temp_path = extract_chunk(LOCAL_AUDIO, vc["start"], vc["end"])
            os.replace(temp_path, audio_path)

        samples.append({
            "audio_path": audio_path,
            "text": vc["text"],
            "sample_id": sample_id,
            "duration": get_wav_duration(audio_path),
        })
        count += 1
        
        if count % 5 == 0:
            print(f"    {count}/{n_samples} chunk hazırlandı...")

    print(f"  TAMAM: {len(samples)} lokal örnek başarıyla hazırlandı.")
    return samples


# =============================================================================
# AZURE SPEECH TRANSCRIPTION
# =============================================================================

def azure_transcribe(audio_path: str, config: dict) -> str:
    language = config.get("language", "en-US")
    profanity = config.get("profanity", "raw")
    endpoint_type = config.get("endpoint", "conversation")
    output_format = config.get("format", "simple")

    url = (
        f"https://{AZURE_REGION}.stt.speech.microsoft.com/"
        f"speech/recognition/{endpoint_type}/cognitiveservices/v1"
        f"?language={language}&profanity={profanity}&format={output_format}"
    )
    
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
        "Accept": "application/json",
    }

    try:
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        for attempt in range(3):
            response = httpx.post(url, headers=headers, content=audio_data, timeout=120.0)
            
            if response.status_code == 429:
                wait = int(response.headers.get("retry-after", 2 ** attempt * 5))
                print(f"      [Rate Limit] {wait}s bekleniyor...")
                time.sleep(wait)
                continue
                
            if response.status_code == 200:
                res_json = response.json()
                if output_format == "detailed":
                    nbest = res_json.get("NBest", [])
                    if nbest:
                        return nbest[0].get("Display", "").strip()
                else:
                    if res_json.get("RecognitionStatus") == "Success":
                        return res_json.get("DisplayText", "").strip()
                break
    except Exception as e:
        print(f"      Azure isteği hatası: {e}")
        
    return ""


# =============================================================================
# RANDOM SEARCH
# =============================================================================

def run_random_search(samples: list) -> tuple:
    param_space = {
        "language": ["en-US", "en-GB"],
        "profanity": ["raw", "masked"],
        "format": ["simple", "detailed"],
        "endpoint": ["conversation", "dictation"],
    }

    rng = np.random.RandomState(RANDOM_SEED)
    configs = list(ParameterSampler(param_space, n_iter=N_RANDOM_CONFIGS, random_state=rng))

    print(f"\n{'-'*70}")
    print(f"  RANDOM SEARCH — {N_RANDOM_CONFIGS} konfigürasyon x {len(samples)} örnek")
    print(f"{'-'*70}")

    all_results = []

    for cfg_idx, config in enumerate(configs):
        config_label = (
            f"lang={config['language']} | prof={config['profanity']} | "
            f"fmt={config['format']} | ep={config['endpoint']}"
        )
        print(f"\n  [{cfg_idx+1}/{N_RANDOM_CONFIGS}] {config_label}")

        wer_scores = []
        cer_scores = []
        errors = 0

        for sample in samples:
            try:
                hyp_raw = azure_transcribe(sample["audio_path"], config)
                ref_norm = normalize_text(sample["text"])
                hyp_norm = normalize_text(hyp_raw)

                if not hyp_norm or not ref_norm:
                    errors += 1
                    continue

                wer_val = jiwer.wer(ref_norm, hyp_norm)
                cer_val = jiwer.cer(ref_norm, hyp_norm)
                wer_scores.append(wer_val)
                cer_scores.append(cer_val)

            except Exception as e:
                errors += 1
                print(f"      HATA ({sample['sample_id']}): {e}")

        if wer_scores:
            avg_wer = np.mean(wer_scores)
            avg_cer = np.mean(cer_scores)
            std_wer = np.std(wer_scores)
        else:
            avg_wer = 1.0
            avg_cer = 1.0
            std_wer = 0.0

        result = {
            "config_idx": cfg_idx,
            "config": config,
            "avg_wer": round(float(avg_wer), 4),
            "avg_cer": round(float(avg_cer), 4),
            "std_wer": round(float(std_wer), 4),
            "n_success": len(wer_scores),
            "n_errors": errors,
            "wer_scores": [round(w, 4) for w in wer_scores],
            "cer_scores": [round(c, 4) for c in cer_scores],
        }
        all_results.append(result)

        status = f"WER={avg_wer:.4f} (+/-{std_wer:.4f}) | CER={avg_cer:.4f} | ok={len(wer_scores)} err={errors}"
        print(f"    -> {status}")

    best = min(all_results, key=lambda x: x["avg_wer"])
    
    print(f"\n{'-'*70}")
    print(f"  EN İYİ KONFİGÜRASYON (WER bazında)")
    print(f"{'-'*70}")
    print(f"  Config #{best['config_idx']}:")
    for k, v in best["config"].items():
        print(f"    {k}: {v}")
    print(f"  Avg WER : {best['avg_wer']:.4f} (%{best['avg_wer']*100:.2f})")
    print(f"  Avg CER : {best['avg_cer']:.4f} (%{best['avg_cer']*100:.2f})")
    print(f"{'-'*70}")

    return best["config"], all_results


# =============================================================================
# FINAL DEĞERLENDİRME
# =============================================================================

def run_final_evaluation(samples: list, best_config: dict) -> list:
    print(f"\n{'-'*70}")
    print(f"  FINAL DEĞERLENDİRME — {len(samples)} örnek")
    print(f"  Konfigürasyon: {best_config}")
    print(f"{'-'*70}")

    results = []

    for i, sample in enumerate(samples):
        print(f"\n  [{i+1}/{len(samples)}] {sample['sample_id']} ({sample['duration']:.1f}s)")
        
        result = {
            "sample_id": sample["sample_id"],
            "duration": round(sample["duration"], 2),
            "ref_text": sample["text"],
            "status": "success",
            "error": None,
        }

        try:
            t0 = time.time()
            hyp_raw = azure_transcribe(sample["audio_path"], best_config)
            proc_time = time.time() - t0

            ref_norm = normalize_text(sample["text"])
            hyp_norm = normalize_text(hyp_raw)

            if not hyp_norm:
                result["status"] = "empty_hypothesis"
                result["wer"] = 1.0
                result["cer"] = 1.0
                results.append(result)
                print(f"    UYARI: Boş transkript!")
                continue

            wer_val = jiwer.wer(ref_norm, hyp_norm)
            cer_val = jiwer.cer(ref_norm, hyp_norm)
            measures = jiwer.process_words(ref_norm, hyp_norm)

            result.update({
                "hyp_text": hyp_raw,
                "wer": round(wer_val, 4),
                "cer": round(cer_val, 4),
                "insertions": measures.insertions,
                "deletions": measures.deletions,
                "substitutions": measures.substitutions,
                "hits": measures.hits,
                "ref_words": len(ref_norm.split()),
                "hyp_words": len(hyp_norm.split()),
                "time": round(proc_time, 2),
                "rtf": round(proc_time / sample["duration"], 4) if sample["duration"] > 0 else 0,
            })

            total_errors = measures.insertions + measures.deletions + measures.substitutions
            if total_errors > 0:
                result["insertion_ratio"] = round(measures.insertions / total_errors, 4)
                result["deletion_ratio"] = round(measures.deletions / total_errors, 4)
                result["substitution_ratio"] = round(measures.substitutions / total_errors, 4)

            print(f"    WER={wer_val:.4f} | CER={cer_val:.4f} | "
                  f"Ins={measures.insertions} Del={measures.deletions} Sub={measures.substitutions} | "
                  f"{proc_time:.1f}s")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            result["wer"] = None
            result["cer"] = None
            print(f"    HATA: {e}")
            traceback.print_exc()

        results.append(result)

    return results


# =============================================================================
# RAPORLAMA
# =============================================================================

def print_final_report(results: list, best_config: dict):
    valid = [r for r in results if r["status"] == "success" and r.get("wer") is not None]
    
    if not valid:
        print("\n  HATA: Geçerli sonuç yok!")
        return

    wer_vals = [r["wer"] for r in valid]
    cer_vals = [r["cer"] for r in valid]

    avg_wer = np.mean(wer_vals)
    avg_cer = np.mean(cer_vals)
    std_wer = np.std(wer_vals)
    std_cer = np.std(cer_vals)
    
    total_ins = sum(r.get("insertions", 0) for r in valid)
    total_del = sum(r.get("deletions", 0) for r in valid)
    total_sub = sum(r.get("substitutions", 0) for r in valid)
    total_hits = sum(r.get("hits", 0) for r in valid)
    total_errors = total_ins + total_del + total_sub

    print(f"\n\n{'-'*70}")
    print(f"  AZURE SPEECH STT — FINAL WER/CER RAPORU")
    print(f"{'-'*70}")
    print(f"  Tarih          : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Corpus         : AMI Meeting Corpus (Local, {MEETING_ID})")
    print(f"  Örnek Sayısı   : {len(valid)} / {len(results)}")
    print(f"{'-'*70}")
    print(f"  Konfigürasyon:")
    for k, v in best_config.items():
        print(f"    {k:20s}: {v}")
    print(f"{'-'*70}")
    print(f"  GENEL METRİKLER:")
    print(f"    Ortalama WER : {avg_wer:.4f}  (%{avg_wer*100:.2f}) +/-{std_wer:.4f}")
    print(f"    Ortalama CER : {avg_cer:.4f}  (%{avg_cer*100:.2f}) +/-{std_cer:.4f}")
    print(f"    Medyan WER   : {np.median(wer_vals):.4f}")
    print(f"    Min WER      : {np.min(wer_vals):.4f}")
    print(f"    Max WER      : {np.max(wer_vals):.4f}")
    print(f"{'-'*70}")
    print(f"  HATA DEKOMPOZİSYONU (Toplam):")
    print(f"    Insertions   : {total_ins:>6} ({total_ins/total_errors*100:.1f}%)" if total_errors > 0 else "")
    print(f"    Deletions    : {total_del:>6} ({total_del/total_errors*100:.1f}%)" if total_errors > 0 else "")
    print(f"    Substitutions: {total_sub:>6} ({total_sub/total_errors*100:.1f}%)" if total_errors > 0 else "")
    print(f"    Hits (Doğru) : {total_hits:>6}")
    print(f"    Toplam Hata  : {total_errors:>6}")
    print(f"{'-'*70}")

    print(f"\n  {'Sample':<16} {'Dur(s)':<8} {'WER':<8} {'CER':<8} {'Ins':<6} {'Del':<6} {'Sub':<6} {'Hits':<6} {'RTF':<8}")
    print(f"  {'-'*78}")
    for r in valid:
        print(f"  {r['sample_id']:<16} "
              f"{r['duration']:<8.1f} "
              f"{r['wer']:<8.4f} "
              f"{r['cer']:<8.4f} "
              f"{r.get('insertions', '-'):<6} "
              f"{r.get('deletions', '-'):<6} "
              f"{r.get('substitutions', '-'):<6} "
              f"{r.get('hits', '-'):<6} "
              f"{r.get('rtf', '-'):<8}")
    print(f"{'-'*70}")


def save_results(all_search_results: list, best_config: dict, final_results: list):
    search_path = os.path.join(RESULTS_DIR, "randomsearch_all_configs.json")
    with open(search_path, "w", encoding="utf-8") as f:
        json.dump(all_search_results, f, ensure_ascii=False, indent=2)
    print(f"\n  TAMAM: RandomSearch sonuçları: {search_path}")

    best_path = os.path.join(RESULTS_DIR, "best_azure_config.json")
    with open(best_path, "w", encoding="utf-8") as f:
        json.dump(best_config, f, ensure_ascii=False, indent=2)
    print(f"  TAMAM: En iyi konfigürasyon : {best_path}")

    report_path = os.path.join(RESULTS_DIR, "azure_wer_cer_report.json")
    valid = [r for r in final_results if r.get("wer") is not None]
    report = {
        "timestamp": datetime.now().isoformat(),
        "corpus": f"AMI Meeting Corpus (Local, {MEETING_ID})",
        "model": "Azure Speech STT",
        "best_config": best_config,
        "summary": {
            "n_samples": len(valid),
            "avg_wer": round(float(np.mean([r["wer"] for r in valid])), 4) if valid else None,
            "avg_cer": round(float(np.mean([r["cer"] for r in valid])), 4) if valid else None,
            "std_wer": round(float(np.std([r["wer"] for r in valid])), 4) if valid else None,
            "median_wer": round(float(np.median([r["wer"] for r in valid])), 4) if valid else None,
        },
        "per_sample": final_results,
    }
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  TAMAM: Final rapor (JSON)   : {report_path}")

    csv_path = os.path.join(RESULTS_DIR, "azure_wer_cer_report.csv")
    with open(csv_path, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Sample", "Duration", "Status", "WER", "CER",
            "Insertions", "Deletions", "Substitutions", "Hits",
            "Ref_Words", "Hyp_Words", "Time", "RTF", "Error"
        ])
        for r in final_results:
            writer.writerow([
                r.get("sample_id", ""),
                r.get("duration", ""),
                r.get("status", ""),
                r.get("wer", ""),
                r.get("cer", ""),
                r.get("insertions", ""),
                r.get("deletions", ""),
                r.get("substitutions", ""),
                r.get("hits", ""),
                r.get("ref_words", ""),
                r.get("hyp_words", ""),
                r.get("time", ""),
                r.get("rtf", ""),
                r.get("error", ""),
            ])
    print(f"  TAMAM: Final rapor (CSV)    : {csv_path}")


# =============================================================================
# ANA PIPELINE
# =============================================================================

def main():
    print("=" * 70)
    print("  AMI Corpus — Azure Speech RandomSearch + WER/CER Analizi (Local Data)")
    print("=" * 70)

    if not AZURE_KEY:
        print("HATA: AZURE_SPEECH_KEY tanımlı değil!")
        sys.exit(1)

    print(f"  Azure Region : {AZURE_REGION}")
    print(f"  RandomSearch : {N_RANDOM_CONFIGS} konfigürasyon x {N_SEARCH_SAMPLES} örnek")
    print(f"  Final Test   : {N_FINAL_SAMPLES} örnek")

    print(f"\n{'-'*70}")
    print("  ADIM 1: Lokal AMI Corpus Hazırlama")
    print(f"{'-'*70}")
    
    max_samples = max(N_SEARCH_SAMPLES, N_FINAL_SAMPLES)
    all_samples = load_local_ami_samples(max_samples)
    
    if len(all_samples) < N_SEARCH_SAMPLES:
        print(f"HATA: Yeterli örnek yüklenemedi ({len(all_samples)}/{N_SEARCH_SAMPLES})")
        sys.exit(1)

    search_samples = all_samples[:N_SEARCH_SAMPLES]
    final_samples = all_samples[:N_FINAL_SAMPLES]

    print(f"\n{'-'*70}")
    print("  ADIM 2: RandomSearch Hiperparametre Taraması")
    print(f"{'-'*70}")
    
    best_config, all_search_results = run_random_search(search_samples)

    print(f"\n{'-'*70}")
    print("  ADIM 3: Final WER/CER Değerlendirmesi")
    print(f"{'-'*70}")
    
    final_results = run_final_evaluation(final_samples, best_config)

    print(f"\n{'-'*70}")
    print("  ADIM 4: Raporlama")
    print(f"{'-'*70}")
    
    print_final_report(final_results, best_config)
    save_results(all_search_results, best_config, final_results)

    print(f"\n{'-'*70}")
    print("  TAMAM: Pipeline başarıyla sonlandı!")
    print(f"{'-'*70}")


if __name__ == "__main__":
    main()

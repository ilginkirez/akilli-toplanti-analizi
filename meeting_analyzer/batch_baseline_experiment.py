"""
batch_baseline_experiment.py
----------------------------
Çoklu toplantı (batch) WER/CER karşılaştırma testi.
İçinde 'ground_truth' klasörü olan tüm toplantıları bulur, 
her biri için baseline_experiment çalıştırır ve genel ortalamayı hesaplar.
"""

import argparse
import glob
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from baseline_experiment import run_experiment

def run_batch_experiment(base_dirs):
    print("="*80)
    print(" TOPLU (BATCH) WER/CER TESTİ BAŞLIYOR ")
    print("="*80)

    # Toplantı klasörlerini bul (içinde ground_truth klasörü olanlar)
    meeting_dirs = []
    for base_dir in base_dirs:
        # bundles altındaki tüm klasörleri tara
        for d in glob.glob(os.path.join(base_dir, "*")):
            if os.path.isdir(d):
                gt_dir = os.path.join(d, "ground_truth")
                if os.path.exists(gt_dir):
                    meeting_dirs.append(d)

    if not meeting_dirs:
        print("HATA: Hiçbir toplantı klasöründe 'ground_truth' bulunamadı.")
        return

    print(f"{len(meeting_dirs)} adet test edilebilir toplantı bulundu:\n")
    for d in meeting_dirs:
        print(f" - {os.path.basename(d)}")
    print("-" * 80)

    all_results = {}
    total_metrics = {
        "individual_wer": [],
        "individual_cer": [],
        "mixed_wer": [],
        "mixed_cer": []
    }

    for meeting_dir in meeting_dirs:
        meeting_name = os.path.basename(meeting_dir)
        print(f"\n>>> TEST BAŞLIYOR: {meeting_name}")
        
        # Dosya yollarını bul
        # Ses dosyaları recordings/<meeting_id>/individual/ altında
        # meeting_dir formatı: Deneme_iki__meet-m-3cb35cc2
        # Klasör adını parse etmeye gerek yok, glob ile bulalım
        indiv_dir = glob.glob(os.path.join(meeting_dir, "recordings", "*", "individual"))
        if not indiv_dir:
            print(f"  Atlanıyor: Individual ses klasörü bulunamadı.")
            continue
        audio_dir = indiv_dir[0]

        gt_dir = os.path.join(meeting_dir, "ground_truth")
        
        # ref_map oluştur (ses_dosyasi_adi.ogg = ref_dosyasi_path)
        # Biliyoruz ki ref_ilgin.txt -> Ilgın'ın .ogg dosyası, ref_merve.txt -> Merve'nin .ogg dosyası
        # Ama OGG dosyalarının adı dinamik. 
        # Bunu ai/transcript.json'dan okuyup eşleştirelim
        transcript_path = glob.glob(os.path.join(meeting_dir, "recordings", "*", "analysis", "ai", "transcript.json"))
        
        ref_map = {}
        if transcript_path:
            with open(transcript_path[0], "r", encoding="utf-8") as f:
                t_data = json.load(f)
                for source in t_data.get("sources", []):
                    name = source.get("display_name", "").lower()
                    file_path = source.get("file_path", "")
                    basename = os.path.basename(file_path)
                    
                    if "ılgın" in name or "ilgin" in name:
                        ref_file = os.path.join(gt_dir, "ref_ilgin.txt")
                        if os.path.exists(ref_file):
                            with open(ref_file, "r", encoding="utf-8") as rf:
                                ref_map[basename] = rf.read()
                    elif "merve" in name:
                        ref_file = os.path.join(gt_dir, "ref_merve.txt")
                        if os.path.exists(ref_file):
                            with open(ref_file, "r", encoding="utf-8") as rf:
                                ref_map[basename] = rf.read()

        ref_mixed_path = os.path.join(gt_dir, "ref_mixed.txt")
        ref_mixed_text = None
        if os.path.exists(ref_mixed_path):
            with open(ref_mixed_path, "r", encoding="utf-8") as f:
                ref_mixed_text = f.read()

        # Deneyi çalıştır
        try:
            results = run_experiment(audio_dir, ref_map, ref_mixed_text)
            all_results[meeting_name] = results
            
            # Ortalama metrikleri topla
            # JSON'dan oku
            json_path = os.path.join(os.path.dirname(audio_dir), "baseline_experiment_results.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    r_data = json.load(f)
                    
                    # Individual Ortalamaları
                    if "per_speaker" in r_data:
                        wers = [m["filtered_wer"] for m in r_data["per_speaker"].values() if m.get("filtered_wer") is not None]
                        cers = [m["filtered_cer"] for m in r_data["per_speaker"].values() if m.get("filtered_cer") is not None]
                        if wers: total_metrics["individual_wer"].append(sum(wers)/len(wers))
                        if cers: total_metrics["individual_cer"].append(sum(cers)/len(cers))

                    # Mixed Ortalamaları
                    c_wer = r_data.get("D: Mixed + Filter KAPALI", {}).get("wer")
                    c_cer = r_data.get("D: Mixed + Filter KAPALI", {}).get("cer")
                    if c_wer is not None: total_metrics["mixed_wer"].append(c_wer)
                    if c_cer is not None: total_metrics["mixed_cer"].append(c_cer)

        except Exception as e:
            print(f"HATA: {meeting_name} testi başarısız oldu: {e}")

    # Toplu Grafikleri Çiz
    if all_results:
        _draw_batch_comparison(total_metrics)

def _draw_batch_comparison(metrics):
    print("\n" + "="*80)
    print(" TÜM TOPLANTILARIN GENEL ORTALAMASI (MACRO-AVERAGE) ")
    print("="*80)
    
    avg_indiv_wer = sum(metrics["individual_wer"])/len(metrics["individual_wer"]) if metrics["individual_wer"] else 0
    avg_mixed_wer = sum(metrics["mixed_wer"])/len(metrics["mixed_wer"]) if metrics["mixed_wer"] else 0
    
    avg_indiv_cer = sum(metrics["individual_cer"])/len(metrics["individual_cer"]) if metrics["individual_cer"] else 0
    avg_mixed_cer = sum(metrics["mixed_cer"])/len(metrics["mixed_cer"]) if metrics["mixed_cer"] else 0

    print(f"Toplam Test Edilen Toplantı Sayısı: {len(metrics['individual_wer'])}")
    print("-" * 80)
    print(f"{'Metrik':<20} {'Individual (Önerilen)':<25} {'Mixed (Geleneksel)':<20} {'İyileştirme'}")
    print("-" * 80)
    
    imp_wer = ((avg_mixed_wer - avg_indiv_wer) / avg_mixed_wer * 100) if avg_mixed_wer > 0 else 0
    imp_cer = ((avg_mixed_cer - avg_indiv_cer) / avg_mixed_cer * 100) if avg_mixed_cer > 0 else 0
    
    print(f"{'Ortalama WER':<20} %{avg_indiv_wer*100:<24.1f} %{avg_mixed_wer*100:<19.1f} %{imp_wer:.1f}")
    print(f"{'Ortalama CER':<20} %{avg_indiv_cer*100:<24.1f} %{avg_mixed_cer*100:<19.1f} %{imp_cer:.1f}")
    print("="*80)

    # Grafik
    labels = ['Ortalama WER\n(Kelime Hatası)', 'Ortalama CER\n(Karakter Hatası)']
    indiv_vals = [avg_indiv_wer, avg_indiv_cer]
    mixed_vals = [avg_mixed_wer, avg_mixed_cer]

    x = range(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 6))
    rects1 = ax.bar([i - width/2 for i in x], indiv_vals, width, label='İzole Kanal (Önerilen)', color='#2ecc71', edgecolor='black')
    rects2 = ax.bar([i + width/2 for i in x], mixed_vals, width, label='Tek Kanal (Geleneksel)', color='#e74c3c', edgecolor='black')

    ax.set_ylabel('Hata Oranı (Düşük = Daha İyi)', fontweight='bold')
    ax.set_title('Birden Fazla Toplantı İçin STT Performans Karşılaştırması\n(Macro-Average)', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontweight='bold')
    ax.legend()

    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'%{height*100:.1f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontweight='bold')

    autolabel(rects1)
    autolabel(rects2)

    fig.tight_layout()
    out_path = os.path.join(current_dir, "batch_overall_comparison.png")
    plt.savefig(out_path, dpi=300)
    print(f"\n[GRAFİK KAYDEDİLDİ]: {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_dirs", nargs='+', required=True, help="bundles klasörlerinin yolları")
    args = parser.parse_args()
    
    run_batch_experiment(args.base_dirs)

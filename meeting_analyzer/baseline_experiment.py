"""
baseline_experiment.py
----------------------
Akademik A/B/C/D Deney Tasarimi:
  A) Individual (izole kanal) + Filter ACIK   -> Bizim sistem
  B) Individual (izole kanal) + Filter KAPALI  -> Filtre etkisi olcumu
  C) Mixed (tek kanal)        + Filter ACIK    -> Geleneksel yontem + filtre
  D) Mixed (tek kanal)        + Filter KAPALI  -> Ham geleneksel yontem

Kullanim:
  python baseline_experiment.py --audio_dir <individual_ses_klasoru> \\
      --ref_map speaker1.ogg=ref1.txt --ref_map speaker2.ogg=ref2.txt \\
      --ref_mixed combined_ref.txt

Cikti:
  - Konsola 4 kosulun karsilastirma tablosu
  - baseline_experiment_results.json  (ham veriler)
  - baseline_comparison_plot.png      (gorsel karsilastirma)
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    import jiwer
    HAS_JIWER = True
except ImportError:
    HAS_JIWER = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False

import src.services.ai_transcription as transcriber


# ---------------------------------------------------------------------------
# Yardimci Fonksiyonlar
# ---------------------------------------------------------------------------

def mix_audio_files(input_files: list[str], output_path: str) -> bool:
    """FFmpeg ile birden fazla ses dosyasini tek kanala (mixed) birlestir."""
    if len(input_files) < 2:
        import shutil
        shutil.copy2(input_files[0], output_path)
        return True

    inputs = []
    for f in input_files:
        inputs.extend(["-i", f])

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", f"amix=inputs={len(input_files)}:duration=longest",
        "-ar", "16000",
        "-ac", "1",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception as e:
        print(f"FFmpeg mix hatasi: {e}")
        return False


def transcribe_and_collect(audio_path: str, language: str = "tr"):
    """Tek bir ses dosyasini Whisper'a gonder. Ham segment listesi dondur."""
    processed_path = transcriber._preprocess_audio(audio_path)
    is_temp = processed_path != audio_path
    try:
        payload = transcriber._request_transcription(processed_path, language=language)
        segments = payload.get("segments", [])
        return segments
    finally:
        if is_temp and os.path.exists(processed_path):
            os.remove(processed_path)


def apply_filter(segments: list, strict: bool = True) -> list:
    """Segmentlere filtreleme uygula veya uygulama."""
    if not strict:
        return [s for s in segments if (s.get("text") or "").strip()]

    filtered = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        lp = transcriber._coerce_float(seg.get("avg_logprob"))
        nsp = transcriber._coerce_float(seg.get("no_speech_prob"))
        if lp is not None and lp < transcriber.MIN_AVG_LOGPROB:
            continue
        if nsp is not None and nsp > transcriber.MAX_NO_SPEECH_PROB:
            continue
        if not transcriber._is_segment_meaningful(text, min_words=transcriber.MIN_SEGMENT_WORDS):
            continue
        filtered.append(seg)
    return filtered


def segments_to_text(segments: list) -> str:
    """Segment listesini birlesmis metin olarak dondur."""
    parts = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if text:
            parts.append(text)
    return " ".join(parts)


def compute_metrics(segments: list, ref_text: str = None) -> dict:
    """Bir kosulun metriklerini hesapla."""
    logprobs = []
    no_speech_probs = []
    for seg in segments:
        lp = transcriber._coerce_float(seg.get("avg_logprob"))
        nsp = transcriber._coerce_float(seg.get("no_speech_prob"))
        if lp is not None:
            logprobs.append(lp)
        if nsp is not None:
            no_speech_probs.append(nsp)

    full_text = segments_to_text(segments)
    word_count = len(full_text.split()) if full_text else 0

    result = {
        "segment_count": len(segments),
        "word_count": word_count,
        "avg_logprob_mean": round(float(sum(logprobs) / len(logprobs)), 4) if logprobs else None,
        "avg_logprob_min": round(float(min(logprobs)), 4) if logprobs else None,
        "no_speech_prob_mean": round(float(sum(no_speech_probs) / len(no_speech_probs)), 4) if no_speech_probs else None,
        "no_speech_prob_max": round(float(max(no_speech_probs)), 4) if no_speech_probs else None,
        "full_text": full_text,
    }

    if ref_text and HAS_JIWER and full_text:
        ref = ref_text.strip().lower()
        hyp = full_text.strip().lower()
        result["wer"] = round(jiwer.wer(ref, hyp), 4)
        result["cer"] = round(jiwer.cer(ref, hyp), 4)

        # --- Hata Dekompozisyonu (He & Whitehill 2025) ---
        measures = jiwer.process_words(ref, hyp)
        ins = measures.insertions
        dels = measures.deletions
        subs = measures.substitutions
        hits = measures.hits
        total_errors = ins + dels + subs

        result["insertions"] = ins
        result["deletions"] = dels
        result["substitutions"] = subs
        result["hits"] = hits
        result["total_errors"] = total_errors
        result["insertion_ratio"] = round(ins / total_errors, 4) if total_errors > 0 else 0.0
        result["deletion_ratio"] = round(dels / total_errors, 4) if total_errors > 0 else 0.0
        result["substitution_ratio"] = round(subs / total_errors, 4) if total_errors > 0 else 0.0

    return result


# ---------------------------------------------------------------------------
# Ana Deney Fonksiyonu
# ---------------------------------------------------------------------------

def run_experiment(audio_dir: str, ref_map: dict, ref_mixed_text: str = None):
    """
    4 kosullu A/B/C/D deneyini calistir.
    
    ref_map: { "dosya_adi.ogg": "referans metni" }
             Her konusmacinin izole ses dosyasi -> ground truth eslemesi
    ref_mixed_text: Mixed audio icin birlesik ground truth
    """

    # 1. Ses dosyalarini bul
    audio_files = []
    for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac"):
        audio_files.extend(glob.glob(os.path.join(audio_dir, ext)))

    if not audio_files:
        print(f"HATA: {audio_dir} klasorunde ses dosyasi bulunamadi.")
        return

    print(f"Bulunan ses dosyalari ({len(audio_files)} adet):")
    for af in audio_files:
        print(f"  - {os.path.basename(af)}")

    # 2. Mixed (tek kanal) dosya uret
    print("\n[1/5] FFmpeg ile mixed audio uretiliyor...")
    mixed_path = os.path.join(audio_dir, "_mixed_baseline.wav")
    if not mix_audio_files(audio_files, mixed_path):
        print("HATA: Mixed audio uretilemedi.")
        return
    print(f"  -> {mixed_path}")

    # 3. Individual transkripsiyon (her dosya ayri + konusmaci bazli WER)
    print("\n[2/5] Individual transkripsiyon (izole kanallar)...")
    individual_segments = []
    per_speaker_wer = {}

    for af in audio_files:
        basename = os.path.basename(af)
        print(f"  Whisper cagiriliyor: {basename}")
        try:
            segs = transcribe_and_collect(af)
            individual_segments.extend(segs)
            print(f"    -> {len(segs)} segment")

            # Konusmaci bazli WER hesapla
            speaker_ref = ref_map.get(basename)
            if speaker_ref and HAS_JIWER:
                filtered_segs = apply_filter(segs, strict=True)
                unfiltered_segs = apply_filter(segs, strict=False)

                hyp_filtered = segments_to_text(filtered_segs).strip().lower()
                hyp_unfiltered = segments_to_text(unfiltered_segs).strip().lower()
                ref_lower = speaker_ref.strip().lower()

                per_speaker_wer[basename] = {
                    "ref_words": len(ref_lower.split()),
                    "filtered_wer": round(jiwer.wer(ref_lower, hyp_filtered), 4) if hyp_filtered else None,
                    "filtered_cer": round(jiwer.cer(ref_lower, hyp_filtered), 4) if hyp_filtered else None,
                    "unfiltered_wer": round(jiwer.wer(ref_lower, hyp_unfiltered), 4) if hyp_unfiltered else None,
                    "unfiltered_cer": round(jiwer.cer(ref_lower, hyp_unfiltered), 4) if hyp_unfiltered else None,
                }
                # Hata dekompozisyonu (filtrelenmis icin)
                if hyp_filtered:
                    m = jiwer.process_words(ref_lower, hyp_filtered)
                    total_err = m.insertions + m.deletions + m.substitutions
                    per_speaker_wer[basename]["insertions"] = m.insertions
                    per_speaker_wer[basename]["deletions"] = m.deletions
                    per_speaker_wer[basename]["substitutions"] = m.substitutions
                    per_speaker_wer[basename]["insertion_ratio"] = round(m.insertions / total_err, 4) if total_err > 0 else 0.0
        except Exception as e:
            print(f"    HATA: {e}")

    # 4. Mixed transkripsiyon
    print("\n[3/5] Mixed transkripsiyon (tek kanal)...")
    try:
        mixed_segments = transcribe_and_collect(mixed_path)
        print(f"  -> {len(mixed_segments)} segment")
    except Exception as e:
        print(f"  HATA: {e}")
        mixed_segments = []

    # 5. Birlesmis referans metni olustur (individual icin)
    combined_individual_ref = None
    if ref_map:
        # Dosya sirasina gore birlestir
        ref_parts = []
        for af in audio_files:
            bn = os.path.basename(af)
            if bn in ref_map:
                ref_parts.append(ref_map[bn])
        if ref_parts:
            combined_individual_ref = " ".join(ref_parts)

    # 6. 4 Kosulun Metriklerini Hesapla
    print("\n[4/5] Metrikler hesaplaniyor...")

    conditions = {
        "A: Individual + Filter ACIK": (
            apply_filter(individual_segments, strict=True),
            combined_individual_ref
        ),
        "B: Individual + Filter KAPALI": (
            apply_filter(individual_segments, strict=False),
            combined_individual_ref
        ),
        "C: Mixed + Filter ACIK": (
            apply_filter(mixed_segments, strict=True),
            ref_mixed_text
        ),
        "D: Mixed + Filter KAPALI": (
            apply_filter(mixed_segments, strict=False),
            ref_mixed_text
        ),
    }

    results = {}
    for label, (segs, ref) in conditions.items():
        metrics = compute_metrics(segs, ref)
        results[label] = metrics

    # -------------------------------------------------------------------
    # Konusmaci Bazli WER Tablosu
    # -------------------------------------------------------------------
    if per_speaker_wer:
        print("\n" + "=" * 80)
        print(" KONUSMACI BAZLI WER/CER (Individual Kanal - Adil Karsilastirma)")
        print("=" * 80)
        print(f"{'Dosya':<45} {'Ref':>4} {'WER(F)':>8} {'CER(F)':>8} {'WER(U)':>8} {'CER(U)':>8}")
        print("-" * 80)

        total_wer_f = []
        total_cer_f = []
        total_wer_u = []
        total_cer_u = []

        for fname, m in per_speaker_wer.items():
            wf = m.get("filtered_wer")
            cf = m.get("filtered_cer")
            wu = m.get("unfiltered_wer")
            cu = m.get("unfiltered_cer")

            if wf is not None: total_wer_f.append(wf)
            if cf is not None: total_cer_f.append(cf)
            if wu is not None: total_wer_u.append(wu)
            if cu is not None: total_cer_u.append(cu)

            print(
                f"{fname:<45} "
                f"{m['ref_words']:>4} "
                f"{wf if wf is not None else '-':>8} "
                f"{cf if cf is not None else '-':>8} "
                f"{wu if wu is not None else '-':>8} "
                f"{cu if cu is not None else '-':>8}"
            )

        # Ortalama
        if total_wer_f:
            avg_wf = sum(total_wer_f) / len(total_wer_f)
            avg_cf = sum(total_cer_f) / len(total_cer_f)
            avg_wu = sum(total_wer_u) / len(total_wer_u)
            avg_cu = sum(total_cer_u) / len(total_cer_u)
            print("-" * 80)
            print(
                f"{'ORTALAMA':<45} "
                f"{'':>4} "
                f"{avg_wf:>8.4f} "
                f"{avg_cf:>8.4f} "
                f"{avg_wu:>8.4f} "
                f"{avg_cu:>8.4f}"
            )
        print("=" * 80)
        print("  (F) = Filter ACIK,  (U) = Filter KAPALI (Unfiltered)")

    # -------------------------------------------------------------------
    # Mixed WER Tablosu
    # -------------------------------------------------------------------
    if ref_mixed_text and HAS_JIWER:
        print("\n" + "=" * 80)
        print(" MIXED KANAL WER/CER (Geleneksel Yontem)")
        print("=" * 80)
        c_wer = results["C: Mixed + Filter ACIK"].get("wer", "-")
        c_cer = results["C: Mixed + Filter ACIK"].get("cer", "-")
        d_wer = results["D: Mixed + Filter KAPALI"].get("wer", "-")
        d_cer = results["D: Mixed + Filter KAPALI"].get("cer", "-")
        print(f"  Mixed + Filter ACIK   : WER={c_wer}  CER={c_cer}")
        print(f"  Mixed + Filter KAPALI : WER={d_wer}  CER={d_cer}")
        print("=" * 80)

    # -------------------------------------------------------------------
    # Genel Karsilastirma Tablosu (Logprob / NoSpeech)
    # -------------------------------------------------------------------
    print("\n" + "=" * 90)
    print(" GENEL METRIK KARSILASTIRMASI (4 KOSUL)")
    print("=" * 90)
    header = f"{'Kosul':<35} {'Seg':>5} {'Kelime':>7} {'AvgLP':>8} {'MinLP':>8} {'NSP_avg':>8} {'NSP_max':>8}"
    print(header)
    print("-" * 90)

    for label, m in results.items():
        row = (
            f"{label:<35} "
            f"{m['segment_count']:>5} "
            f"{m['word_count']:>7} "
            f"{m['avg_logprob_mean'] or 0:>8.4f} "
            f"{m['avg_logprob_min'] or 0:>8.4f} "
            f"{m['no_speech_prob_mean'] or 0:>8.4f} "
            f"{m['no_speech_prob_max'] or 0:>8.4f}"
        )
        print(row)
    print("=" * 90)

    # -------------------------------------------------------------------
    # Akademik Yorum
    # -------------------------------------------------------------------
    a_lp = results["A: Individual + Filter ACIK"].get("avg_logprob_mean")
    d_lp = results["D: Mixed + Filter KAPALI"].get("avg_logprob_mean")
    
    print("\n[AKADEMIK YORUM]")
    if a_lp and d_lp:
        if a_lp > d_lp:
            print(f"  -> Logprob: Individual ({a_lp:.4f}) > Mixed ({d_lp:.4f})")
            print(f"     Model izole kanalda %{abs(a_lp-d_lp)/abs(d_lp)*100:.1f} daha emin.")
        else:
            print(f"  -> Logprob: Individual ({a_lp:.4f}) vs Mixed ({d_lp:.4f})")

    if per_speaker_wer and total_wer_f:
        avg_indiv_wer = sum(total_wer_f) / len(total_wer_f)
        mixed_wer = results["D: Mixed + Filter KAPALI"].get("wer")
        if mixed_wer is not None:
            if avg_indiv_wer < mixed_wer:
                imp = (mixed_wer - avg_indiv_wer) / mixed_wer * 100
                print(f"  -> WER (Adil): Individual ort. = %{avg_indiv_wer*100:.1f}, Mixed = %{mixed_wer*100:.1f}")
                print(f"     Izole kanal mimarisi WER'i %{imp:.1f} azaltmistir.")
            else:
                print(f"  -> WER (Adil): Individual ort. = %{avg_indiv_wer*100:.1f}, Mixed = %{mixed_wer*100:.1f}")

    # -------------------------------------------------------------------
    # Hata Dekompozisyonu Tablosu (He & Whitehill 2025)
    # -------------------------------------------------------------------
    has_decomp = any(r.get("insertions") is not None for r in results.values())
    if has_decomp:
        print("\n" + "=" * 95)
        print(" HATA DEKOMPOZISYONU (Ins/Del/Sub) — He & Whitehill 2025")
        print("=" * 95)
        print(f"{'Kosul':<35} {'Ins':>6} {'Del':>6} {'Sub':>6} {'Total':>7} {'Ins%':>7} {'Del%':>7} {'Sub%':>7}")
        print("-" * 95)
        for label, m in results.items():
            if m.get("insertions") is not None:
                print(
                    f"{label:<35} "
                    f"{m['insertions']:>6} "
                    f"{m['deletions']:>6} "
                    f"{m['substitutions']:>6} "
                    f"{m['total_errors']:>7} "
                    f"{m['insertion_ratio']*100:>6.1f}% "
                    f"{m['deletion_ratio']*100:>6.1f}% "
                    f"{m['substitution_ratio']*100:>6.1f}%"
                )
        print("=" * 95)

    # -------------------------------------------------------------------
    # Leakage-Insertion Korelasyon Analizi
    # -------------------------------------------------------------------
    if per_speaker_wer:
        ins_ratios = [m.get("insertion_ratio", 0) for m in per_speaker_wer.values() if m.get("insertion_ratio") is not None]
        if ins_ratios:
            avg_ins_ratio = sum(ins_ratios) / len(ins_ratios)
            print("\n" + "=" * 80)
            print(" LEAKAGE-INSERTION KORELASYON ANALIZI")
            print("=" * 80)
            for fname, m in per_speaker_wer.items():
                ir = m.get("insertion_ratio")
                if ir is not None:
                    flag = " *** LEAKAGE SUPHELISI" if ir > 0.60 else ""
                    print(f"  {fname:<40} Ins%={ir*100:>5.1f}%{flag}")
            print("-" * 80)
            print(f"  Ortalama Insertion Orani: %{avg_ins_ratio*100:.1f}")
            if avg_ins_ratio > 0.60:
                print("  [!] YUKSEK INSERTION ORANI: Cross-talk/leakage gostergesi.")
                print("      Cozum: Cross-channel enerji karsilastirmasi veya")
                print("      daha agresif no_speech_prob esigi oneriliyor.")
            elif avg_ins_ratio > 0.40:
                print("  [i] ORTA INSERTION ORANI: Kismi leakage olabilir.")
            else:
                print("  [OK] DUSUK INSERTION ORANI: Leakage etkisi sinirli.")
            print("=" * 80)

    # 7. JSON Kaydet
    json_path = os.path.join(os.path.dirname(audio_dir), "baseline_experiment_results.json")
    json_out = {}
    for label, m in results.items():
        m_copy = {k: v for k, v in m.items() if k != "full_text"}
        json_out[label] = m_copy
    json_out["per_speaker"] = per_speaker_wer

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_out, f, indent=2, ensure_ascii=False)
    print(f"\n[JSON]: {json_path}")

    # 8. Gorsel Karsilastirma
    if HAS_PLOT:
        print("\n[5/5] Karsilastirma grafigi ciziliyor...")
        _draw_comparison(results, per_speaker_wer, ref_mixed_text is not None and HAS_JIWER, audio_dir)

    # 9. Gecici mixed dosyayi temizle
    if os.path.exists(mixed_path):
        os.remove(mixed_path)

    return results


def _draw_comparison(results: dict, per_speaker: dict, has_mixed_wer: bool, audio_dir: str):
    """4 kosulun bar chart + konusmaci bazli WER karsilastirmasi."""
    labels_full = list(results.keys())
    labels_short = ["A\nIndiv+Filt", "B\nIndiv-Filt", "C\nMix+Filt", "D\nMix-Filt"]
    colors = ["#2ecc71", "#3498db", "#e67e22", "#e74c3c"]

    # Alt grafik sayisi: 3 temel + 1 WER (konusmaci bazli varsa)
    n_plots = 4 if (per_speaker or has_mixed_wer) else 3
    fig, axes = plt.subplots(1, n_plots, figsize=(5 * n_plots, 5))

    seg_counts = [results[l]["segment_count"] for l in labels_full]
    logprobs = [abs(results[l]["avg_logprob_mean"] or 0) for l in labels_full]
    nsp_means = [results[l]["no_speech_prob_mean"] or 0 for l in labels_full]

    # 1) Segment Sayisi
    axes[0].bar(labels_short, seg_counts, color=colors, edgecolor="black", linewidth=0.5)
    axes[0].set_title("Segment Sayisi", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("Adet")
    for i, v in enumerate(seg_counts):
        axes[0].text(i, v + 0.3, str(v), ha="center", fontweight="bold")

    # 2) |Logprob|
    axes[1].bar(labels_short, logprobs, color=colors, edgecolor="black", linewidth=0.5)
    axes[1].set_title("|Avg Logprob| (dusuk=iyi)", fontsize=12, fontweight="bold")
    axes[1].set_ylabel("|Logprob|")
    for i, v in enumerate(logprobs):
        axes[1].text(i, v + 0.005, f"{v:.3f}", ha="center", fontweight="bold", fontsize=9)

    # 3) No Speech Prob
    axes[2].bar(labels_short, nsp_means, color=colors, edgecolor="black", linewidth=0.5)
    axes[2].set_title("No Speech Prob (dusuk=iyi)", fontsize=12, fontweight="bold")
    axes[2].set_ylabel("Oran")
    for i, v in enumerate(nsp_means):
        axes[2].text(i, v + 0.002, f"{v:.3f}", ha="center", fontweight="bold", fontsize=9)

    # 4) WER Karsilastirmasi (Konusmaci bazli vs Mixed)
    if n_plots == 4:
        wer_labels = []
        wer_values = []
        wer_colors_sub = []

        # Individual konusmaci bazli ortalama
        if per_speaker:
            indiv_wers = [m["filtered_wer"] for m in per_speaker.values() if m.get("filtered_wer") is not None]
            if indiv_wers:
                wer_labels.append("A\nIndiv(spk)")
                wer_values.append(sum(indiv_wers) / len(indiv_wers))
                wer_colors_sub.append("#2ecc71")

            indiv_wers_u = [m["unfiltered_wer"] for m in per_speaker.values() if m.get("unfiltered_wer") is not None]
            if indiv_wers_u:
                wer_labels.append("B\nIndiv(spk)")
                wer_values.append(sum(indiv_wers_u) / len(indiv_wers_u))
                wer_colors_sub.append("#3498db")

        # Mixed WER
        if has_mixed_wer:
            c_wer = results["C: Mixed + Filter ACIK"].get("wer")
            d_wer = results["D: Mixed + Filter KAPALI"].get("wer")
            if c_wer is not None:
                wer_labels.append("C\nMixed")
                wer_values.append(c_wer)
                wer_colors_sub.append("#e67e22")
            if d_wer is not None:
                wer_labels.append("D\nMixed")
                wer_values.append(d_wer)
                wer_colors_sub.append("#e74c3c")

        if wer_values:
            axes[3].bar(wer_labels, wer_values, color=wer_colors_sub, edgecolor="black", linewidth=0.5)
            axes[3].set_title("WER (dusuk=iyi)", fontsize=12, fontweight="bold")
            axes[3].set_ylabel("Oran")
            for i, v in enumerate(wer_values):
                axes[3].text(i, v + 0.01, f"{v:.3f}", ha="center", fontweight="bold", fontsize=9)

    fig.suptitle("A/B/C/D Baseline Karsilastirma Deneyi (Konusmaci Bazli)", fontsize=14, fontweight="bold")
    plt.tight_layout()

    out_path = os.path.join(os.path.dirname(audio_dir), "baseline_comparison_plot.png")
    plt.savefig(out_path, dpi=300)
    print(f"  -> Grafik kaydedildi: {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Akademik A/B/C/D Baseline Karsilastirma Deneyi"
    )
    parser.add_argument(
        "--audio_dir", required=True,
        help="Individual ses dosyalarinin bulundugu klasor"
    )
    parser.add_argument(
        "--ref_map", action="append", default=[],
        help="Konusmaci bazli referans: dosya.ogg=referans.txt (tekrarlanabilir)"
    )
    parser.add_argument(
        "--ref_mixed", type=str, default=None,
        help="Mixed audio icin birlesik ground truth (.txt)"
    )
    args = parser.parse_args()

    # ref_map parse
    ref_map = {}
    for entry in args.ref_map:
        if "=" not in entry:
            print(f"UYARI: Gecersiz ref_map formati (= eksik): {entry}")
            continue
        audio_name, ref_path = entry.split("=", 1)
        with open(ref_path, "r", encoding="utf-8") as f:
            ref_map[audio_name] = f.read()

    ref_mixed_text = None
    if args.ref_mixed:
        with open(args.ref_mixed, "r", encoding="utf-8") as f:
            ref_mixed_text = f.read()

    run_experiment(args.audio_dir, ref_map, ref_mixed_text)

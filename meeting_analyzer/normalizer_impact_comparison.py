"""
normalizer_impact_comparison.py
-------------------------------
Turkce normalizer'in WER uzerindeki etkisini olcer.
Ayni Whisper ciktisini kullanarak:
  - ESKİ: Ham metin (normalizasyonsuz)
  - YENİ: Turkce normalizer uygulanmis metin
karsilastirir.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jiwer
from src.services.turkish_normalizer import (
    normalize_turkish_asr_output,
    normalize_for_wer,
)


def load_transcript_by_speaker(transcript_path: str) -> dict[str, list[str]]:
    """transcript.json'dan konusmaci bazli segment metinlerini yukle."""
    with open(transcript_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    speaker_texts = {}
    pid_to_name = {}
    for src in data.get("sources", []):
        pid_to_name[src["participant_id"]] = src["display_name"]

    for seg in data.get("segments", []):
        pid = seg.get("participant_id", "")
        name = pid_to_name.get(pid, pid)
        text = seg.get("text", "").strip()
        if text:
            speaker_texts.setdefault(name, []).append(text)

    return speaker_texts


def compute_wer_detailed(ref: str, hyp: str) -> dict:
    """WER + Ins/Del/Sub hesapla."""
    if not ref or not hyp:
        return {"wer": 1.0, "ins": 0, "del": 0, "sub": 0, "hits": 0}
    w = jiwer.process_words(ref, hyp)
    total = w.insertions + w.deletions + w.substitutions
    return {
        "wer": round(jiwer.wer(ref, hyp), 4),
        "ins": w.insertions,
        "del": w.deletions,
        "sub": w.substitutions,
        "hits": w.hits,
        "total_errors": total,
        "ins_pct": round(w.insertions / total * 100, 1) if total > 0 else 0,
        "del_pct": round(w.deletions / total * 100, 1) if total > 0 else 0,
        "sub_pct": round(w.substitutions / total * 100, 1) if total > 0 else 0,
    }


def run_comparison(meeting_dir: str, ref_map: dict[str, str]):
    """
    Ayni Whisper ciktisi uzerinde normalizer etkisini olc.

    ref_map: { "display_name": "ref_dosya_yolu" }
    """
    transcript_path = os.path.join(meeting_dir, "analysis", "ai", "transcript.json")
    if not os.path.exists(transcript_path):
        print(f"HATA: transcript.json bulunamadi: {transcript_path}")
        return

    speaker_texts = load_transcript_by_speaker(transcript_path)

    print("=" * 100)
    print(" TURKCE NORMALIZER ETKI ANALIZI (Onceki vs Sonraki)")
    print("=" * 100)

    all_old_wer = []
    all_new_wer = []

    for speaker_name, ref_path in ref_map.items():
        with open(ref_path, "r", encoding="utf-8") as f:
            ref_raw = f.read().strip()

        hyp_segments = speaker_texts.get(speaker_name, [])
        if not hyp_segments:
            print(f"\n  [!] {speaker_name} icin segment bulunamadi.")
            continue

        hyp_raw = " ".join(hyp_segments)

        # --- ESKI: Normalizasyonsuz (sadece lowercase + noktalama kaldir) ---
        ref_old = ref_raw.lower()
        hyp_old = hyp_raw.lower()

        # --- YENI: Turkce normalizer uygulanmis ---
        ref_new = normalize_for_wer(ref_raw)
        hyp_new = normalize_for_wer(normalize_turkish_asr_output(hyp_raw))

        old_metrics = compute_wer_detailed(ref_old, hyp_old)
        new_metrics = compute_wer_detailed(ref_new, hyp_new)

        all_old_wer.append(old_metrics["wer"])
        all_new_wer.append(new_metrics["wer"])

        wer_delta = new_metrics["wer"] - old_metrics["wer"]
        wer_pct_change = (wer_delta / old_metrics["wer"] * 100) if old_metrics["wer"] > 0 else 0

        print(f"\n  {'-' * 90}")
        print(f"  KONUSMACI: {speaker_name}")
        print(f"  {'-' * 90}")
        print(f"  Referans kelime  : {len(ref_old.split())}")
        print(f"  Hipotez kelime   : {len(hyp_old.split())} (ham) / {len(hyp_new.split())} (norm)")
        print()
        print(f"  {'Metrik':<20} {'ESKI (ham)':<18} {'YENI (norm)':<18} {'Degisim':<15}")
        print(f"  {'-'*70}")
        print(f"  {'WER':<20} {old_metrics['wer']*100:<17.2f}% {new_metrics['wer']*100:<17.2f}% {wer_pct_change:>+.1f}%")
        print(f"  {'Insertions':<20} {old_metrics['ins']:<17} {new_metrics['ins']:<17} {new_metrics['ins']-old_metrics['ins']:>+d}")
        print(f"  {'Deletions':<20} {old_metrics['del']:<17} {new_metrics['del']:<17} {new_metrics['del']-old_metrics['del']:>+d}")
        print(f"  {'Substitutions':<20} {old_metrics['sub']:<17} {new_metrics['sub']:<17} {new_metrics['sub']-old_metrics['sub']:>+d}")
        print(f"  {'Hits (Dogru)':<20} {old_metrics['hits']:<17} {new_metrics['hits']:<17} {new_metrics['hits']-old_metrics['hits']:>+d}")

        # Ornek farklar goster
        ref_old_words = ref_old.split()
        ref_new_words = ref_new.split()
        hyp_old_words = hyp_old.split()
        hyp_new_words = hyp_new.split()

        # Normalizasyonun degistirdigi kelimeleri bul
        changed_words = []
        for i, (old_w, new_w) in enumerate(zip(hyp_old_words, hyp_new_words)):
            if old_w != new_w:
                changed_words.append((old_w, new_w))
        if changed_words:
            print(f"\n  Normalizasyonun degistirdigi kelimeler (ilk 10):")
            for old_w, new_w in changed_words[:10]:
                try:
                    print(f"    '{old_w}' -> '{new_w}'")
                except UnicodeEncodeError:
                    print(f"    [unicode karakter] -> [normalize edildi]")

    # Genel ozet
    if all_old_wer and all_new_wer:
        avg_old = sum(all_old_wer) / len(all_old_wer)
        avg_new = sum(all_new_wer) / len(all_new_wer)
        delta = avg_new - avg_old
        pct = (delta / avg_old * 100) if avg_old > 0 else 0

        print(f"\n{'=' * 100}")
        print(f" GENEL OZET")
        print(f"{'=' * 100}")
        print(f"  Ortalama WER (ESKI) : %{avg_old*100:.2f}")
        print(f"  Ortalama WER (YENI) : %{avg_new*100:.2f}")
        print(f"  Degisim             : {pct:>+.2f}%")
        print()
        if delta < 0:
            print(f"  [IYILESME] Turkce normalizer WER'i %{abs(pct):.1f} azaltti.")
        elif delta == 0:
            print(f"  [NOTR] Turkce normalizer bu veri setinde WER'i degistirmedi.")
            print(f"         Neden: Whisper zaten Turkce karakterleri dogru uretiyor olabilir.")
            print(f"         Etki daha cok uretim pipeline'inda 'evet/tamam' gibi kisa")
            print(f"         onaylamalarin korunmasinda gorunecektir.")
        else:
            print(f"  [DIKKAT] Turkce normalizer WER'i %{abs(pct):.1f} artirdi.")
            print(f"           Normalizasyon kurallari gozden gecirilmeli.")
        print(f"{'=' * 100}")


if __name__ == "__main__":
    MEETING_DIR = r"c:\Users\HP\Desktop\akilli-toplanti-analizi\meeting_analyzer\recordings\meet-m-62478a64"
    REF_MAP = {
        "Merve Çatalkaya": os.path.join(MEETING_DIR, "ground_truth", "ref_merve.txt"),
        "Ilgın Kirez": os.path.join(MEETING_DIR, "ground_truth", "ref_ilgin.txt"),
    }
    run_comparison(MEETING_DIR, REF_MAP)

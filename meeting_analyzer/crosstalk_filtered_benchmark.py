"""
crosstalk_filtered_benchmark.py
--------------------------------
AMI Meeting Corpus — Crosstalk-Filtered Local Whisper Benchmark

Tez Katkısı:
  Close-talk headset kanallarında görülen crosstalk etkisini azaltmak için
  kanal baskınlığına dayalı (channel dominance) bir ön işleme adımı uygular.

  Hedef kanalın (Headset-0 = Speaker A) enerjisi diğer kanallara göre
  yeterince baskın değilse, ilgili ses bölgesi crosstalk olarak
  değerlendirilir ve transkripsiyon öncesinde bastırılır.

Algoritma:
  1. Tüm 4 headset kanalı indirilir (Headset-0..3)
  2. frame_ms'lik pencereler halinde RMS enerji hesaplanır
  3. Headset-0 enerjisi > max(diğerleri) + margin_db ise pencere tutulur
  4. Aksi halde pencere sessizleştirilir (zero-fill)
  5. Filtrelenmiş audio → Faster-Whisper → WER

Kullanım:
  python crosstalk_filtered_benchmark.py
  python crosstalk_filtered_benchmark.py --margin_db 10  # daha agresif
"""

import argparse
import os
import random
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import jiwer
import soundfile as sf
from tqdm import tqdm
from faster_whisper import WhisperModel

# ══════════════════════════════════════════════════════════════════════════════
# KONFİGÜRASYON
# ══════════════════════════════════════════════════════════════════════════════
RANDOM_SEED = 42
DEFAULT_N_SAMPLES = 5
HEADSET_CHANNELS = [0, 1, 2, 3]  # AMI'de 4 konuşmacı

AMI_MEETING_POOL = [
    f"ES{num}{sess}"
    for num in range(2002, 2017)
    for sess in ["a", "b", "c", "d"]
]

AMI_AUDIO_BASE = "https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus"
AMI_ANNOTATIONS_ZIP_URL = (
    "https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/"
    "ami_public_manual_1.6.2.zip"
)

DATA_DIR = Path("data/ami_randomized")
ANNOTATIONS_CACHE = DATA_DIR / "annotations_cache"

AMI_INITIAL_PROMPT = (
    "This is an English meeting transcription from the AMI Meeting Corpus. "
    "The speakers discuss product design, user interface, remote control, "
    "prototype, buttons, LCD display, agenda, decisions, tasks, and actions. "
    "Transcribe only the spoken words accurately."
)


# ══════════════════════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ══════════════════════════════════════════════════════════════════════════════

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"\([^\)]+\)", " ", text)
    text = re.sub(r"[^a-z0-9'\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def select_meetings(pool, n, seed):
    rng = random.Random(seed)
    return sorted(rng.sample(pool, n))


# ── Veri İndirme ──────────────────────────────────────────────────────────────

def download_headset(meeting_id: str, channel: int) -> Path | None:
    """AMI mirror'dan belirtilen headset kanalını indirir."""
    audio_dir = DATA_DIR / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{meeting_id}.Headset-{channel}.wav"
    out_path = audio_dir / fname

    if out_path.exists():
        return out_path

    url = f"{AMI_AUDIO_BASE}/{meeting_id}/audio/{fname}"
    print(f"    [İNDİR] {fname} ...")
    try:
        urllib.request.urlretrieve(url, str(out_path))
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"    [OK]    {size_mb:.1f} MB")
    except Exception as e:
        print(f"    [HATA]  {fname}: {e}")
        if out_path.exists():
            out_path.unlink()
        return None
    return out_path


def download_all_headsets(meeting_id: str) -> dict[int, Path]:
    """Tüm headset kanallarını indirir. {channel: path} döner."""
    paths = {}
    for ch in HEADSET_CHANNELS:
        p = download_headset(meeting_id, ch)
        if p:
            paths[ch] = p
    return paths


# ── Annotation ────────────────────────────────────────────────────────────────

def download_and_extract_annotations(meeting_ids: list) -> dict:
    ANNOTATIONS_CACHE.mkdir(parents=True, exist_ok=True)
    needed = {}
    for mid in meeting_ids:
        xml_name = f"{mid}.A.words.xml"
        cached = ANNOTATIONS_CACHE / xml_name
        needed[mid] = cached if cached.exists() else None

    missing = [mid for mid, p in needed.items() if p is None]
    if not missing:
        return needed

    zip_cache = DATA_DIR / "ami_public_manual_1.6.2.zip"
    if not zip_cache.exists():
        print(f"\n  Annotation zip indiriliyor...")
        try:
            urllib.request.urlretrieve(AMI_ANNOTATIONS_ZIP_URL, str(zip_cache))
        except Exception as e:
            print(f"  [HATA] {e}")
            return needed

    try:
        with zipfile.ZipFile(str(zip_cache), "r") as zf:
            all_names = zf.namelist()
            for mid in missing:
                xml_name = f"{mid}.A.words.xml"
                matches = [n for n in all_names if n.endswith(xml_name)]
                if matches:
                    data = zf.read(matches[0])
                    out = ANNOTATIONS_CACHE / xml_name
                    out.write_bytes(data)
                    needed[mid] = out
    except Exception as e:
        print(f"  [HATA] Zip: {e}")

    return needed


def parse_words_xml(xml_path: Path) -> str:
    try:
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
    except ET.ParseError:
        raw = xml_path.read_text(encoding="utf-8", errors="ignore")
        raw = re.sub(r'xmlns:nite="[^"]+"', '', raw)
        raw = raw.replace("nite:", "")
        root = ET.fromstring(raw)

    words = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "w" and elem.text:
            w = elem.text.strip()
            if w:
                words.append(w)
    return " ".join(words)


def prepare_reference(meeting_id, annotations):
    xml_path = annotations.get(meeting_id)
    if not xml_path or not xml_path.exists():
        return None
    ref = parse_words_xml(xml_path)
    if not ref:
        return None
    ref_dir = DATA_DIR / "reference"
    ref_dir.mkdir(parents=True, exist_ok=True)
    (ref_dir / f"{meeting_id}_SpeakerA.txt").write_text(ref, encoding="utf-8")
    return ref


# ══════════════════════════════════════════════════════════════════════════════
# CROSSTALK FİLTRESİ
# ══════════════════════════════════════════════════════════════════════════════

def rms_energy_db(signal: np.ndarray) -> float:
    """Sinyalin RMS enerjisini dB cinsinden hesaplar."""
    rms = np.sqrt(np.mean(signal.astype(np.float64) ** 2))
    if rms < 1e-10:
        return -100.0
    return 20.0 * np.log10(rms)


def apply_crosstalk_filter(
    target_path: Path,
    other_paths: list[Path],
    margin_db: float = 6.0,
    frame_ms: int = 500,
) -> Path:
    """
    Kanal baskınlığı (channel dominance) tabanlı crosstalk filtresi.

    Her frame_ms'lik pencerede:
      - target kanalın RMS enerjisi hesaplanır
      - diğer kanalların max RMS enerjisi hesaplanır
      - target > max(others) + margin_db ise pencere tutulur
      - aksi halde pencere sessizleştirilir (sıfırlanır)
    """
    # Hedef kanalı oku
    target_data, sr = sf.read(str(target_path), dtype="float32")
    if target_data.ndim > 1:
        target_data = target_data[:, 0]

    # Diğer kanalları oku
    others = []
    for p in other_paths:
        d, _ = sf.read(str(p), dtype="float32")
        if d.ndim > 1:
            d = d[:, 0]
        # Uzunluk eşitle
        min_len = min(len(target_data), len(d))
        others.append(d[:min_len])

    # Tüm kanalları aynı uzunluğa getir
    if others:
        min_len = min(len(target_data), *(len(o) for o in others))
        target_data = target_data[:min_len]
        others = [o[:min_len] for o in others]
    else:
        # Eğer diğer kanal yoksa crosstalk hesabı yapılamaz
        print("      [UYARI] Diğer kanallar yok, filtre uygulanamıyor!")
        min_len = len(target_data)

    frame_size = int(sr * frame_ms / 1000)
    n_frames = len(target_data) // frame_size
    filtered = target_data.copy()

    kept_frames = 0
    silenced_frames = 0

    for i in range(n_frames):
        start = i * frame_size
        end = start + frame_size

        target_db = rms_energy_db(target_data[start:end])
        if others:
            max_other_db = max(rms_energy_db(o[start:end]) for o in others)
        else:
            max_other_db = -100.0

        if target_db > max_other_db + margin_db:
            kept_frames += 1
        else:
            filtered[start:end] = 0.0
            silenced_frames += 1

    # Son kalan kısmı da sessizleştir (güvenli tarafta kal)
    remaining = len(target_data) - n_frames * frame_size
    if remaining > 0:
        filtered[n_frames * frame_size:] = 0.0

    # Filtrelenmiş dosyayı kaydet
    out_dir = DATA_DIR / "audio_filtered"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{target_path.stem}.filtered_{margin_db}dB.wav"
    sf.write(str(out_path), filtered, sr)

    total = kept_frames + silenced_frames
    pct = (silenced_frames / total * 100) if total else 0
    print(
        f"    [FİLTRE] {kept_frames} tutuldu, {silenced_frames} sessizleştirildi "
        f"({pct:.1f}% crosstalk)"
    )

    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# TRANSKRİPSİYON ve METRİK
# ══════════════════════════════════════════════════════════════════════════════

def transcribe_local_whisper(model, audio_path, beam_size=5, use_prompt=True):
    start = time.perf_counter()
    segments, _ = model.transcribe(
        audio_path,
        language="en",
        task="transcribe",
        beam_size=beam_size,
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 300},
        initial_prompt=AMI_INITIAL_PROMPT if use_prompt else None,
    )
    texts = [seg.text.strip() for seg in segments]
    elapsed = time.perf_counter() - start
    return " ".join(texts), elapsed


def calculate_metrics(reference, hypothesis):
    ref_norm = normalize_text(reference)
    hyp_norm = normalize_text(hypothesis)
    if not ref_norm or not hyp_norm:
        return {
            "wer": 1.0, "cer": 1.0,
            "insertions": 0, "deletions": 0, "substitutions": 0,
            "hits": 0, "ref_words": 0, "hyp_words": 0,
        }
    word_out = jiwer.process_words(ref_norm, hyp_norm)
    char_out = jiwer.process_characters(ref_norm, hyp_norm)
    return {
        "wer": word_out.wer, "cer": char_out.cer,
        "insertions": word_out.insertions,
        "deletions": word_out.deletions,
        "substitutions": word_out.substitutions,
        "hits": word_out.hits,
        "ref_words": len(ref_norm.split()),
        "hyp_words": len(hyp_norm.split()),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ANA FONKSİYON
# ══════════════════════════════════════════════════════════════════════════════

def corpus_wer_from_rows(rows):
    """Satırlardan corpus-level WER hesaplar."""
    ti = sum(r["insertions"] for r in rows)
    td = sum(r["deletions"] for r in rows)
    ts = sum(r["substitutions"] for r in rows)
    th = sum(r["hits"] for r in rows)
    total_err = ti + td + ts
    total_ref = th + td + ts
    return total_err / total_ref if total_ref > 0 else 0


def main():
    parser = argparse.ArgumentParser(
        description="AMI Crosstalk-Filtered Benchmark"
    )
    parser.add_argument("--n_samples", type=int, default=DEFAULT_N_SAMPLES)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--margin_db", type=float, default=6.0,
                        help="Channel dominance eşiği (dB)")
    parser.add_argument("--frame_ms", type=int, default=500,
                        help="Enerji penceresi (ms)")
    parser.add_argument("--beam_size", type=int, default=5)
    args = parser.parse_args()

    print("=" * 70)
    print("  CROSSTALK-FILTERED AMI BENCHMARK")
    print("  (Kanal Baskınlığı Tabanlı Ön İşleme)")
    print("=" * 70)
    print(f"  Seed          : {args.seed}")
    print(f"  Margin (dB)   : {args.margin_db}")
    print(f"  Frame (ms)    : {args.frame_ms}")
    print(f"  Beam size     : {args.beam_size}")
    print("=" * 70)

    # ── 1. Rastgele Seçim ─────────────────────────────────────────────────
    selected = select_meetings(AMI_MEETING_POOL, args.n_samples, args.seed)
    print(f"\n  Seçilen toplantılar: {selected}")

    # ── 2. TÜM Headset Kanallarını İndir ─────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  TÜM HEADSET KANALLARI İNDİRİLİYOR (4 kanal × 5 toplantı)")
    print(f"{'─' * 70}")

    all_headsets = {}  # {meeting_id: {ch: Path}}
    for mid in selected:
        print(f"\n  {mid}:")
        paths = download_all_headsets(mid)
        if 0 in paths:
            all_headsets[mid] = paths
        else:
            print(f"  [UYARI] {mid}: Headset-0 indirilemedi, atlaniyor")

    # ── 3. Referans Metinler ──────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  REFERANS METİNLER")
    print(f"{'─' * 70}")

    annotations = download_and_extract_annotations(list(all_headsets.keys()))
    references = {}
    for mid in all_headsets:
        ref = prepare_reference(mid, annotations)
        if ref:
            references[mid] = ref

    valid = [m for m in selected if m in all_headsets and m in references]
    if not valid:
        print("\n[HATA] Geçerli test verisi yok!")
        return

    print(f"\n  ✓ {len(valid)} toplantı hazır: {valid}")

    # ── 4. Crosstalk Filtresi Uygula ─────────────────────────────────────
    print(f"\n{'═' * 70}")
    print(f"  CROSSTALK FİLTRESİ UYGULAN (margin={args.margin_db}dB)")
    print(f"{'═' * 70}")

    filtered_paths = {}
    for mid in valid:
        headsets = all_headsets[mid]
        target = headsets[0]
        others = [headsets[ch] for ch in [1, 2, 3] if ch in headsets]

        if len(others) < 3:
            print(f"  [UYARI] {mid}: Bazı kanallar eksik ({len(others)}/3)")

        print(f"\n  {mid}:")
        fp = apply_crosstalk_filter(
            target, others,
            margin_db=args.margin_db,
            frame_ms=args.frame_ms,
        )
        filtered_paths[mid] = fp

    # ── 5. Model Yükle ve Benchmark Çalıştır ─────────────────────────────
    print(f"\n{'═' * 70}")
    print("  MODEL YÜKLENIYOR: Faster-Whisper large-v3 (CPU, int8)")
    print(f"{'═' * 70}")
    model = WhisperModel(
        "large-v3", device="cpu", compute_type="int8",
        cpu_threads=8, num_workers=1,
    )
    print("  Model hazır.\n")

    # ── 5A. Filtrelenmiş Audio ile Test ──────────────────────────────────
    methods = {
        f"Local_Filtered_{args.margin_db}dB_PromptOFF": (False, True),
        f"Local_Filtered_{args.margin_db}dB_PromptON": (True, True),
        "Local_Raw_PromptOFF": (False, False),
    }

    all_results = {}

    for method_name, (use_prompt, use_filtered) in methods.items():
        print(f"\n{'─' * 70}")
        print(f"  YÖNTEM: {method_name}")
        print(f"{'─' * 70}")

        rows = []
        for mid in tqdm(valid, desc=method_name):
            if use_filtered:
                audio_path = str(filtered_paths[mid])
            else:
                audio_path = str(all_headsets[mid][0])

            ref = references[mid]
            hyp, elapsed = transcribe_local_whisper(
                model, audio_path,
                beam_size=args.beam_size,
                use_prompt=use_prompt,
            )
            metrics = calculate_metrics(ref, hyp)

            rows.append({
                "meeting_id": mid,
                "wer": round(metrics["wer"], 4),
                "cer": round(metrics["cer"], 4),
                "insertions": metrics["insertions"],
                "deletions": metrics["deletions"],
                "substitutions": metrics["substitutions"],
                "hits": metrics["hits"],
                "ref_words": metrics["ref_words"],
                "hyp_words": metrics["hyp_words"],
                "time_sec": round(elapsed, 2),
            })
            print(
                f"    {mid}: WER={metrics['wer']*100:.1f}%  "
                f"I={metrics['insertions']} D={metrics['deletions']} "
                f"S={metrics['substitutions']}  ({elapsed:.0f}s)"
            )

        all_results[method_name] = rows
        df = pd.DataFrame(rows)
        out = DATA_DIR / f"results_{method_name}.csv"
        df.to_csv(out, index=False, encoding="utf-8")
        print(f"  → Kaydedildi: {out}")

    del model

    # ── 6. Önceki Sonuçları Yükle (Karşılaştırma İçin) ──────────────────
    prev_files = {
        "Local_Beam5_PromptON": DATA_DIR / "results_Local_Beam5_PromptON.csv",
        "Local_Beam5_PromptOFF": DATA_DIR / "results_Local_Beam5_PromptOFF.csv",
        "Deepgram_Nova2": DATA_DIR / "results_Deepgram_Nova2.csv",
    }
    for name, path in prev_files.items():
        if path.exists():
            df = pd.read_csv(path)
            all_results[name] = df.to_dict("records")

    # ── 7. SONUÇ TABLOSU ─────────────────────────────────────────────────
    print(f"\n\n{'═' * 80}")
    print("  CROSSTALK-FILTERED BENCHMARK — KARŞILAŞTIRMALı SONUÇLAR")
    print(f"  Seed={args.seed}  |  N={len(valid)}  |  Margin={args.margin_db}dB")
    print(f"{'═' * 80}")
    print(
        f"  {'Yöntem':<36} {'WER':>8} {'Ins':>6} {'Del':>6} "
        f"{'Sub':>6} {'Hits':>6} {'Süre':>8}"
    )
    print(f"  {'─' * 76}")

    for method_name, rows in all_results.items():
        df = pd.DataFrame(rows)
        ti = int(df["insertions"].sum())
        td = int(df["deletions"].sum())
        ts = int(df["substitutions"].sum())
        th = int(df["hits"].sum())
        total_err = ti + td + ts
        total_ref = th + td + ts
        cwer = total_err / total_ref if total_ref > 0 else 0
        tt = df["time_sec"].sum()

        print(
            f"  {method_name:<36} {cwer*100:>7.2f}% "
            f"{ti:>6} {td:>6} {ts:>6} {th:>6} {tt:>7.0f}s"
        )

    print(f"  {'─' * 76}")
    print(f"{'═' * 80}")

    # ── Özet CSV ──────────────────────────────────────────────────────────
    summary_rows = []
    for method_name, rows in all_results.items():
        df = pd.DataFrame(rows)
        ti = int(df["insertions"].sum())
        td = int(df["deletions"].sum())
        ts = int(df["substitutions"].sum())
        th = int(df["hits"].sum())
        total_err = ti + td + ts
        total_ref = th + td + ts
        cwer = total_err / total_ref if total_ref > 0 else 0

        summary_rows.append({
            "method": method_name,
            "corpus_wer": round(cwer, 4),
            "insertions": ti, "deletions": td,
            "substitutions": ts, "hits": th,
            "ref_words": total_ref,
            "total_time_sec": round(df["time_sec"].sum(), 2),
            "margin_db": args.margin_db if "Filtered" in method_name else "N/A",
            "n_meetings": len(valid),
            "seed": args.seed,
            "meetings": ",".join(valid),
        })

    sdf = pd.DataFrame(summary_rows)
    spath = DATA_DIR / "crosstalk_benchmark_summary.csv"
    sdf.to_csv(spath, index=False, encoding="utf-8")
    print(f"\n  Özet tablo: {spath}")
    print("  Tez'de kullanılacak karşılaştırma tablosu bu dosyadadır.\n")


if __name__ == "__main__":
    main()

"""
randomized_ami_benchmark.py
----------------------------
AMI Meeting Corpus'tan rastgele (seed=42) seçilmiş 5 toplantı üzerinde
tüm STT yöntemlerini ADİL şekilde karşılaştırır.

Tez Metodolojisi:
  - Seçim      : random.seed(42) → tekrar edilebilir (reproducible)
  - Aynı 5 dosya tüm yöntemlerde kullanılır → adil karşılaştırma
  - Corpus-level WER hesaplanır (micro-average)

Yöntemler:
  A) Lokal Faster-Whisper (Beam=5, Prompt AÇIK)
  B) Lokal Faster-Whisper (Beam=5, Prompt KAPALI)
  C) Deepgram Nova-2 (Bulut API)

Kullanım:
  python randomized_ami_benchmark.py
  python randomized_ami_benchmark.py --n_samples 3   # sadece 3 dosya
"""

import argparse
import io
import os
import random
import re
import time
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import jiwer
import httpx
from tqdm import tqdm
from faster_whisper import WhisperModel

# ══════════════════════════════════════════════════════════════════════════════
# KONFİGÜRASYON
# ══════════════════════════════════════════════════════════════════════════════
RANDOM_SEED = 42
DEFAULT_N_SAMPLES = 5

# AMI Scenario meeting havuzu (ES serisi — hepsinde 4 headset + annotation var)
AMI_MEETING_POOL = [
    f"ES{num}{sess}"
    for num in range(2002, 2017)          # ES2002 .. ES2016
    for sess in ["a", "b", "c", "d"]
]

AMI_AUDIO_BASE = "https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus"
AMI_ANNOTATIONS_ZIP_URL = (
    "https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/"
    "ami_public_manual_1.6.2.zip"
)

DATA_DIR = Path("data/ami_randomized")
ANNOTATIONS_CACHE = DATA_DIR / "annotations_cache"

DEEPGRAM_API_KEY = os.environ.get(
    "DEEPGRAM_API_KEY", "35d9aa2236178355723f86998469bbfab6be674e"
)
DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

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
    """WER karşılaştırması için metin normalizasyonu."""
    text = text.lower()
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"\([^\)]+\)", " ", text)
    text = re.sub(r"[^a-z0-9'\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def select_meetings(pool: list, n: int, seed: int) -> list:
    """Havuzdan rastgele n toplantı seç (tekrar edilebilir)."""
    rng = random.Random(seed)
    selected = rng.sample(pool, n)
    return sorted(selected)


# ── Veri İndirme ──────────────────────────────────────────────────────────────

def download_audio(meeting_id: str) -> Path:
    """AMI mirror'dan Headset-0 ses dosyasını indirir."""
    audio_dir = DATA_DIR / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_path = audio_dir / f"{meeting_id}.Headset-0.wav"

    if out_path.exists():
        print(f"  [CACHE] {out_path.name} zaten mevcut")
        return out_path

    url = f"{AMI_AUDIO_BASE}/{meeting_id}/audio/{meeting_id}.Headset-0.wav"
    print(f"  [İNDİR] {meeting_id} Headset-0 ...")
    try:
        urllib.request.urlretrieve(url, str(out_path))
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"  [OK]    {size_mb:.1f} MB")
    except Exception as e:
        print(f"  [HATA]  İndirme başarısız: {e}")
        if out_path.exists():
            out_path.unlink()
        return None
    return out_path


def download_and_extract_annotations(meeting_ids: list) -> dict:
    """
    AMI annotation zip'inden ilgili words XML dosyalarını çıkarır.
    Döndürülen dict: {meeting_id: Path(words.xml)}
    """
    ANNOTATIONS_CACHE.mkdir(parents=True, exist_ok=True)

    # Hangi XML dosyalarını arıyoruz?
    needed = {}
    for mid in meeting_ids:
        xml_name = f"{mid}.A.words.xml"
        cached = ANNOTATIONS_CACHE / xml_name
        if cached.exists():
            needed[mid] = cached
        else:
            needed[mid] = None

    missing = [mid for mid, p in needed.items() if p is None]

    if missing:
        zip_cache = DATA_DIR / "ami_public_manual_1.6.2.zip"

        if not zip_cache.exists():
            print(f"\n  Annotation zip indiriliyor (bir kez yapılır)...")
            print(f"  URL: {AMI_ANNOTATIONS_ZIP_URL}")
            try:
                urllib.request.urlretrieve(
                    AMI_ANNOTATIONS_ZIP_URL, str(zip_cache)
                )
                size_mb = zip_cache.stat().st_size / (1024 * 1024)
                print(f"  [OK] {size_mb:.1f} MB indirildi")
            except Exception as e:
                print(f"  [HATA] Annotation zip indirilemedi: {e}")
                return needed

        print(f"  Zip'ten {len(missing)} XML çıkarılıyor...")
        try:
            with zipfile.ZipFile(str(zip_cache), "r") as zf:
                all_names = zf.namelist()
                for mid in missing:
                    xml_name = f"{mid}.A.words.xml"
                    # Zip içindeki yolu bul (genelde words/ altında)
                    matches = [
                        n for n in all_names
                        if n.endswith(xml_name)
                    ]
                    if matches:
                        target = matches[0]
                        data = zf.read(target)
                        out = ANNOTATIONS_CACHE / xml_name
                        out.write_bytes(data)
                        needed[mid] = out
                        print(f"    ✓ {xml_name}")
                    else:
                        print(f"    ✗ {xml_name} bulunamadı!")
        except Exception as e:
            print(f"  [HATA] Zip açılamadı: {e}")

    return needed


def parse_words_xml(xml_path: Path) -> str:
    """AMI words XML dosyasından referans metin oluşturur."""
    try:
        tree = ET.parse(str(xml_path))
        root = tree.getroot()
    except ET.ParseError:
        # NXT namespace sorunlarını çöz
        raw = xml_path.read_text(encoding="utf-8", errors="ignore")
        # nite: namespace'ini kaldır
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


def prepare_reference(meeting_id: str, annotations: dict) -> str | None:
    """Bir toplantı için referans metin hazırlar."""
    xml_path = annotations.get(meeting_id)
    if xml_path is None or not xml_path.exists():
        print(f"  [UYARI] {meeting_id} için referans XML yok!")
        return None

    ref = parse_words_xml(xml_path)
    if not ref:
        print(f"  [UYARI] {meeting_id} XML'den metin çıkarılamadı!")
        return None

    # Cache olarak txt kaydet
    ref_dir = DATA_DIR / "reference"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_file = ref_dir / f"{meeting_id}_SpeakerA.txt"
    ref_file.write_text(ref, encoding="utf-8")
    return ref


# ── Transkripsiyon Yöntemleri ─────────────────────────────────────────────────

def transcribe_local_whisper(
    model: WhisperModel,
    audio_path: str,
    beam_size: int = 5,
    use_prompt: bool = True,
) -> tuple[str, float]:
    """Lokal Faster-Whisper ile transkripsiyon. (metin, süre) döner."""
    start = time.perf_counter()
    segments, info = model.transcribe(
        audio_path,
        language="en",
        task="transcribe",
        beam_size=beam_size,
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 300,
        },
        initial_prompt=AMI_INITIAL_PROMPT if use_prompt else None,
    )
    texts = [seg.text.strip() for seg in segments]
    elapsed = time.perf_counter() - start
    return " ".join(texts), elapsed


def transcribe_deepgram(audio_path: str) -> tuple[str, float]:
    """Deepgram Nova-2 API ile transkripsiyon. (metin, süre) döner."""
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/wav",
    }
    params = {
        "language": "en",
        "model": "nova-2",
        "smart_format": "false",
        "punctuate": "false",
    }

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    start = time.perf_counter()
    try:
        resp = httpx.post(
            DEEPGRAM_URL,
            headers=headers,
            params=params,
            content=audio_data,
            timeout=300.0,
        )
        elapsed = time.perf_counter() - start

        if resp.status_code != 200:
            print(f"    [HATA] Deepgram API: {resp.status_code}")
            return "", elapsed

        data = resp.json()
        transcript = (
            data["results"]["channels"][0]["alternatives"][0]["transcript"]
        )
        return transcript, elapsed
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"    [HATA] Deepgram: {e}")
        return "", elapsed


# ── Metrik Hesaplama ──────────────────────────────────────────────────────────

def calculate_metrics(reference: str, hypothesis: str) -> dict:
    """WER, CER ve hata dekompozisyonu hesaplar."""
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
        "wer": word_out.wer,
        "cer": char_out.cer,
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

def main():
    parser = argparse.ArgumentParser(
        description="AMI Randomized Benchmark (Tez Metodolojisi)"
    )
    parser.add_argument(
        "--n_samples", type=int, default=DEFAULT_N_SAMPLES,
        help="Rastgele seçilecek toplantı sayısı"
    )
    parser.add_argument(
        "--seed", type=int, default=RANDOM_SEED,
        help="Rastgele seçim seed değeri"
    )
    parser.add_argument(
        "--skip_deepgram", action="store_true",
        help="Deepgram API'yi atla (sadece lokal test)"
    )
    parser.add_argument(
        "--skip_local", action="store_true",
        help="Lokal Whisper'ı atla (sadece Deepgram test)"
    )
    args = parser.parse_args()

    print("=" * 65)
    print("  RASTGELELEŞTİRİLMİŞ AMI BENCHMARK")
    print("  (Tez Metodolojisi: Adil Karşılaştırma)")
    print("=" * 65)
    print(f"  Seed           : {args.seed}")
    print(f"  Örnek sayısı   : {args.n_samples}")
    print(f"  Havuz büyüklüğü: {len(AMI_MEETING_POOL)} toplantı")
    print("=" * 65)

    # ── 1. Rastgele Seçim ─────────────────────────────────────────────────
    selected = select_meetings(AMI_MEETING_POOL, args.n_samples, args.seed)
    print(f"\n  Seçilen toplantılar (seed={args.seed}):")
    for i, mid in enumerate(selected, 1):
        print(f"    {i}. {mid}")

    # ── 2. Veri İndirme ──────────────────────────────────────────────────
    print(f"\n{'─' * 65}")
    print("  SES DOSYALARI İNDİRİLİYOR")
    print(f"{'─' * 65}")

    audio_paths = {}
    for mid in selected:
        p = download_audio(mid)
        if p:
            audio_paths[mid] = p

    if not audio_paths:
        print("\n[HATA] Hiçbir ses dosyası indirilemedi!")
        return

    print(f"\n{'─' * 65}")
    print("  REFERANS METİNLER HAZIRLANIYOR")
    print(f"{'─' * 65}")

    annotations = download_and_extract_annotations(list(audio_paths.keys()))
    references = {}
    for mid in audio_paths:
        ref = prepare_reference(mid, annotations)
        if ref:
            references[mid] = ref

    # Sadece hem ses hem referansı olan toplantıları tut
    valid_meetings = [m for m in selected if m in audio_paths and m in references]
    if not valid_meetings:
        print("\n[HATA] Geçerli test verisi yok!")
        return

    print(f"\n  ✓ {len(valid_meetings)} toplantı hazır: {valid_meetings}")

    # ── 3. BENCHMARK ─────────────────────────────────────────────────────
    all_results = {}  # method_name -> [row_dicts]

    # ── 3A. Lokal Faster-Whisper ─────────────────────────────────────────
    if not args.skip_local:
        print(f"\n{'═' * 65}")
        print("  MODEL YÜKLENIYOR: Faster-Whisper large-v3 (CPU, int8)")
        print(f"{'═' * 65}")
        model = WhisperModel(
            "large-v3", device="cpu", compute_type="int8",
            cpu_threads=8, num_workers=1,
        )
        print("  Model hazır.\n")

        for method_name, use_prompt in [
            ("Local_Beam5_PromptON", True),
            ("Local_Beam5_PromptOFF", False),
        ]:
            print(f"\n{'─' * 65}")
            print(f"  YÖNTEM: {method_name}")
            print(f"{'─' * 65}")

            rows = []
            for mid in tqdm(valid_meetings, desc=method_name):
                audio_path = str(audio_paths[mid])
                ref = references[mid]

                hyp, elapsed = transcribe_local_whisper(
                    model, audio_path, beam_size=5, use_prompt=use_prompt
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
            # Ara sonuçları kaydet
            df = pd.DataFrame(rows)
            out = DATA_DIR / f"results_{method_name}.csv"
            df.to_csv(out, index=False, encoding="utf-8")
            print(f"  → Kaydedildi: {out}")

        del model  # RAM'i boşalt

    # ── 3B. Deepgram Nova-2 ──────────────────────────────────────────────
    if not args.skip_deepgram:
        print(f"\n{'─' * 65}")
        print("  YÖNTEM: Deepgram Nova-2 (API)")
        print(f"{'─' * 65}")

        rows = []
        for mid in tqdm(valid_meetings, desc="Deepgram"):
            audio_path = str(audio_paths[mid])
            ref = references[mid]

            hyp, elapsed = transcribe_deepgram(audio_path)
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

        all_results["Deepgram_Nova2"] = rows
        df = pd.DataFrame(rows)
        out = DATA_DIR / f"results_Deepgram_Nova2.csv"
        df.to_csv(out, index=False, encoding="utf-8")
        print(f"  → Kaydedildi: {out}")

    # ── 4. SONUÇ TABLOSU ────────────────────────────────────────────────
    print(f"\n\n{'═' * 75}")
    print("  RASTGELELEŞTİRİLMİŞ AMI BENCHMARK — SONUÇLAR")
    print(f"  Seed={args.seed}  |  N={len(valid_meetings)}  |  Toplantılar: {valid_meetings}")
    print(f"{'═' * 75}")
    print(
        f"  {'Yöntem':<28} {'WER':>8} {'Ins':>6} {'Del':>6} "
        f"{'Sub':>6} {'Hits':>6} {'Süre':>8}"
    )
    print(f"  {'─' * 70}")

    for method_name, rows in all_results.items():
        df = pd.DataFrame(rows)
        # Corpus-level WER (micro-average)
        total_ins = df["insertions"].sum()
        total_del = df["deletions"].sum()
        total_sub = df["substitutions"].sum()
        total_hits = df["hits"].sum()
        total_errors = total_ins + total_del + total_sub
        total_ref = total_hits + total_del + total_sub
        corpus_wer = total_errors / total_ref if total_ref > 0 else 0
        total_time = df["time_sec"].sum()

        print(
            f"  {method_name:<28} {corpus_wer*100:>7.2f}% "
            f"{total_ins:>6} {total_del:>6} {total_sub:>6} "
            f"{total_hits:>6} {total_time:>7.0f}s"
        )

    print(f"  {'─' * 70}")
    print(f"  Referans toplam kelime: "
          f"{sum(r['ref_words'] for r in list(all_results.values())[0])}")
    print(f"{'═' * 75}")

    # ── Özet CSV ─────────────────────────────────────────────────────────
    summary_rows = []
    for method_name, rows in all_results.items():
        df = pd.DataFrame(rows)
        total_ins = df["insertions"].sum()
        total_del = df["deletions"].sum()
        total_sub = df["substitutions"].sum()
        total_hits = df["hits"].sum()
        total_errors = total_ins + total_del + total_sub
        total_ref = total_hits + total_del + total_sub
        corpus_wer = total_errors / total_ref if total_ref > 0 else 0

        summary_rows.append({
            "method": method_name,
            "corpus_wer": round(corpus_wer, 4),
            "insertions": total_ins,
            "deletions": total_del,
            "substitutions": total_sub,
            "hits": total_hits,
            "ref_words": total_ref,
            "total_time_sec": round(df["time_sec"].sum(), 2),
            "n_meetings": len(valid_meetings),
            "seed": args.seed,
            "meetings": ",".join(valid_meetings),
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_path = DATA_DIR / "benchmark_summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8")
    print(f"\n  Özet tablo: {summary_path}")
    print(f"  Tez'de kullanılacak tablo bu dosyadadır.\n")


if __name__ == "__main__":
    main()

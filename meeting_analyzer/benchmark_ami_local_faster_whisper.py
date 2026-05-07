"""
benchmark_ami_local_faster_whisper.py
--------------------------------------
AMI Meeting Corpus WER/CER Benchmark — Local Faster-Whisper (CPU, int8)

Groq Cloud API'den bağımsız olarak, lokal CPU üzerinde Faster-Whisper
large-v3 modeli ile AMI Corpus üzerinde WER/CER ölçümü yapar.

Bu script beam_size, condition_on_previous_text, vad_filter gibi
Groq API'de desteklenmeyen parametreleri kullanabilir.

Kullanım:
  py benchmark_ami_local_faster_whisper.py --manifest ami_manifest.csv --beam_size 5
"""

import argparse
import time
import re
from pathlib import Path

import pandas as pd
import jiwer
from tqdm import tqdm
from faster_whisper import WhisperModel


# ── Initial Prompt ────────────────────────────────────────────────────────────
# AMI Corpus İngilizce toplantı kayıtlarıdır. Prompt, modelin bağlamını
# anlamasına yardımcı olur ve teknik terimlerdeki doğruluğu artırır.
AMI_INITIAL_PROMPT = (
    "This is an English meeting transcription from the AMI Meeting Corpus. "
    "The speakers discuss product design, user interface, remote control, "
    "prototype, buttons, LCD display, agenda, decisions, tasks, and actions. "
    "Transcribe only the spoken words accurately."
)


def normalize_text(text: str) -> str:
    """WER karşılaştırması için metin normalizasyonu."""
    text = text.lower()
    text = re.sub(r"\[[^\]]+\]", " ", text)   # [noise], [laughter] vb.
    text = re.sub(r"\([^\)]+\)", " ", text)    # parantez içi açıklamalar
    text = re.sub(r"[^a-z0-9'\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def transcribe_local_faster_whisper(
    model: WhisperModel,
    audio_path: str,
    language: str = "en",
    beam_size: int = 5,
    use_prompt: bool = True,
) -> str:
    """
    Lokal Faster-Whisper ile transkripsiyon.

    Groq API'de desteklenmeyen parametreler burada kullanılabilir:
    - beam_size: Doğruluk için 5, hız için 1
    - condition_on_previous_text: False → insertion hatalarını azaltır
    - vad_filter: True → sessiz kısımları filtreler, hallucination azalır
    - initial_prompt: Bağlam bilgisi → teknik kelime doğruluğu artar
    """
    segments, info = model.transcribe(
        audio_path,
        language=language,
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

    # segments generator olduğu için transkripsiyon burada çalışır
    texts = []
    for segment in segments:
        texts.append(segment.text.strip())

    return " ".join(texts)


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


def main():
    parser = argparse.ArgumentParser(
        description="AMI Meeting Corpus - Local Faster-Whisper CPU Benchmark"
    )
    parser.add_argument(
        "--manifest", required=True,
        help="CSV dosyası: audio_path,reference_path sütunları"
    )
    parser.add_argument("--model", default="large-v3", help="Whisper model adı")
    parser.add_argument("--beam_size", type=int, default=5, help="Beam search boyutu")
    parser.add_argument("--cpu_threads", type=int, default=8, help="CPU thread sayısı")
    parser.add_argument(
        "--output", default="ami_local_faster_whisper_results.csv",
        help="Sonuç CSV dosyası"
    )
    parser.add_argument(
        "--no-prompt", action="store_true",
        help="Initial prompt kullanma (ablation testi için)"
    )
    args = parser.parse_args()

    df = pd.read_csv(args.manifest)

    print("=" * 60)
    print("  LOCAL FASTER-WHISPER CPU BENCHMARK")
    print("=" * 60)
    print(f"  Model          : {args.model}")
    print(f"  Device         : CPU")
    print(f"  Compute type   : int8")
    print(f"  Beam size      : {args.beam_size}")
    print(f"  CPU threads    : {args.cpu_threads}")
    print(f"  Initial prompt : {'OFF' if args.no_prompt else 'ON'}")
    print(f"  VAD filter     : ON")
    print(f"  cond_prev_text : OFF")
    print(f"  Dosya sayısı   : {len(df)}")
    print("=" * 60)

    print("\nModel yükleniyor (ilk seferde HF Hub'dan indirilecek)...")
    model = WhisperModel(
        args.model,
        device="cpu",
        compute_type="int8",
        cpu_threads=args.cpu_threads,
        num_workers=1,
    )
    print("Model hazır.\n")

    rows = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Transkripsiyon"):
        audio_path = str(row["audio_path"])
        reference_path = str(row["reference_path"])

        if not Path(audio_path).exists():
            print(f"  [UYARI] Ses dosyası bulunamadı: {audio_path}")
            continue
        if not Path(reference_path).exists():
            print(f"  [UYARI] Referans dosyası bulunamadı: {reference_path}")
            continue

        reference = Path(reference_path).read_text(encoding="utf-8", errors="ignore")

        start = time.perf_counter()
        hypothesis = transcribe_local_faster_whisper(
            model=model,
            audio_path=audio_path,
            language="en",
            beam_size=args.beam_size,
            use_prompt=not args.no_prompt,
        )
        elapsed = time.perf_counter() - start

        metrics = calculate_metrics(reference, hypothesis)

        rows.append({
            "audio_path": audio_path,
            "reference_path": reference_path,
            "hypothesis": hypothesis,
            "wer": round(metrics["wer"], 4),
            "cer": round(metrics["cer"], 4),
            "insertions": metrics["insertions"],
            "deletions": metrics["deletions"],
            "substitutions": metrics["substitutions"],
            "hits": metrics["hits"],
            "ref_words": metrics["ref_words"],
            "hyp_words": metrics["hyp_words"],
            "processing_time_sec": round(elapsed, 2),
        })

    if not rows:
        print("\n[HATA] Hiçbir dosya işlenemedi!")
        return

    result_df = pd.DataFrame(rows)
    result_df.to_csv(args.output, index=False, encoding="utf-8")

    # ── Corpus-level metrikleri hesapla ─────────────────────────────────────
    total_insertions = result_df["insertions"].sum()
    total_deletions = result_df["deletions"].sum()
    total_substitutions = result_df["substitutions"].sum()
    total_hits = result_df["hits"].sum()

    total_errors = total_insertions + total_deletions + total_substitutions
    total_ref_words = total_hits + total_deletions + total_substitutions

    corpus_wer = total_errors / total_ref_words if total_ref_words else 0
    avg_cer = result_df["cer"].mean()
    total_time = result_df["processing_time_sec"].sum()

    print(f"\n{'=' * 60}")
    print("  SONUÇLAR — LOCAL FASTER-WHISPER CPU")
    print(f"{'=' * 60}")
    print(f"  Model              : {args.model}")
    print(f"  Beam size          : {args.beam_size}")
    print(f"  Compute type       : int8")
    print(f"  Initial prompt     : {'OFF' if args.no_prompt else 'ON'}")
    print(f"{'-' * 60}")
    print(f"  WER (corpus-level) : %{corpus_wer * 100:.2f}")
    print(f"  CER (ortalama)     : %{avg_cer * 100:.2f}")
    print(f"{'-' * 60}")
    print(f"  Insertions         : {total_insertions:>6}")
    print(f"  Deletions          : {total_deletions:>6}")
    print(f"  Substitutions      : {total_substitutions:>6}")
    print(f"  Hits (Doğru)       : {total_hits:>6}")
    print(f"{'-' * 60}")
    print(f"  Referans kelime    : {total_ref_words}")
    print(f"  Toplam süre        : {total_time:.1f} saniye")
    print(f"  Kayıt             : {args.output}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

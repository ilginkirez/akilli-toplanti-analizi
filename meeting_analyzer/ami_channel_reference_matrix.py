"""
ami_channel_reference_matrix.py
-------------------------------
Bir AMI toplantisi icin headset-channel <-> speaker-reference eslesme
matrisini cikarir.

Ornek kullanim:
  python ami_channel_reference_matrix.py --meeting_id ES2002b
  python ami_channel_reference_matrix.py --meeting_id ES2002b --no-prompt
"""

import argparse
import time
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd
from faster_whisper import WhisperModel

from benchmark_ami_local_faster_whisper import (
    calculate_metrics,
    transcribe_local_faster_whisper,
)
from randomized_ami_benchmark import (
    AMI_ANNOTATIONS_ZIP_URL,
    AMI_AUDIO_BASE,
    DATA_DIR,
    parse_words_xml,
)


SPEAKER_IDS = ("A", "B", "C", "D")
HEADSET_IDS = (0, 1, 2, 3)


def parse_channels(raw_value: str) -> tuple[int, ...]:
    """Virgulle ayrilmis kanal listesini parse eder."""
    parts = [part.strip() for part in raw_value.split(",") if part.strip()]
    if not parts:
        raise ValueError("En az bir channel verilmelidir.")

    channels: list[int] = []
    for part in parts:
        channel = int(part)
        if channel not in HEADSET_IDS:
            raise ValueError(f"Gecersiz channel: {channel}")
        channels.append(channel)

    return tuple(dict.fromkeys(channels))


def download_headset_audio(meeting_id: str, headset_id: int) -> Path | None:
    """AMI mirror'dan belirli headset kanalini indirir."""
    audio_dir = DATA_DIR / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_path = audio_dir / f"{meeting_id}.Headset-{headset_id}.wav"

    if out_path.exists():
        print(f"  [CACHE] {out_path.name} zaten mevcut")
        return out_path

    url = f"{AMI_AUDIO_BASE}/{meeting_id}/audio/{meeting_id}.Headset-{headset_id}.wav"
    print(f"  [INDIR] {meeting_id} Headset-{headset_id} ...")
    try:
        urllib.request.urlretrieve(url, str(out_path))
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"  [OK]    {out_path.name} ({size_mb:.1f} MB)")
    except Exception as exc:
        print(f"  [HATA]  {out_path.name} indirilemedi: {exc}")
        if out_path.exists():
            out_path.unlink()
        return None

    return out_path


def download_speaker_references(meeting_id: str) -> dict[str, Path | None]:
    """A/B/C/D words XML dosyalarini indirip cache'e koyar."""
    ref_cache = DATA_DIR / "annotations_cache"
    ref_cache.mkdir(parents=True, exist_ok=True)

    result: dict[str, Path | None] = {}
    missing_speakers: list[str] = []
    for speaker_id in SPEAKER_IDS:
        xml_name = f"{meeting_id}.{speaker_id}.words.xml"
        xml_path = ref_cache / xml_name
        if xml_path.exists():
            result[speaker_id] = xml_path
        else:
            result[speaker_id] = None
            missing_speakers.append(speaker_id)

    if not missing_speakers:
        return result

    zip_cache = DATA_DIR / "ami_public_manual_1.6.2.zip"
    if not zip_cache.exists():
        print("  Annotation zip indiriliyor (bir kez yapilir)...")
        try:
            urllib.request.urlretrieve(AMI_ANNOTATIONS_ZIP_URL, str(zip_cache))
            size_mb = zip_cache.stat().st_size / (1024 * 1024)
            print(f"  [OK] {size_mb:.1f} MB indirildi")
        except Exception as exc:
            print(f"  [HATA] Annotation zip indirilemedi: {exc}")
            return result

    print(f"  Zip'ten {len(missing_speakers)} speaker XML cikariliyor...")
    try:
        with zipfile.ZipFile(str(zip_cache), "r") as zf:
            all_names = zf.namelist()
            for speaker_id in missing_speakers:
                xml_name = f"{meeting_id}.{speaker_id}.words.xml"
                matches = [name for name in all_names if name.endswith(xml_name)]
                if not matches:
                    print(f"    x {xml_name} bulunamadi")
                    continue
                data = zf.read(matches[0])
                out_path = ref_cache / xml_name
                out_path.write_bytes(data)
                result[speaker_id] = out_path
                print(f"    + {xml_name}")
    except Exception as exc:
        print(f"  [HATA] Annotation zip acilamadi: {exc}")

    return result


def prepare_reference_texts(meeting_id: str, xml_paths: dict[str, Path | None]) -> dict[str, str]:
    """XML dosyalarini parse edip speaker bazli referans metin uretir."""
    ref_dir = DATA_DIR / "reference"
    ref_dir.mkdir(parents=True, exist_ok=True)

    texts: dict[str, str] = {}
    for speaker_id, xml_path in xml_paths.items():
        if xml_path is None or not xml_path.exists():
            continue
        text = parse_words_xml(xml_path)
        if not text:
            continue
        texts[speaker_id] = text
        out_path = ref_dir / f"{meeting_id}_Speaker{speaker_id}.txt"
        out_path.write_text(text, encoding="utf-8")
    return texts


def transcribe_single_headset(
    model: WhisperModel,
    audio_path: Path,
    *,
    beam_size: int,
    use_prompt: bool,
) -> tuple[str, float]:
    """Tek bir headset kanali icin transkripsiyon uretir."""
    start = time.perf_counter()
    hypothesis = transcribe_local_faster_whisper(
        model=model,
        audio_path=str(audio_path),
        language="en",
        beam_size=beam_size,
        use_prompt=use_prompt,
        log_prefix=audio_path.name,
        segment_log_every=20,
    )
    elapsed_sec = time.perf_counter() - start
    return hypothesis, elapsed_sec


def build_matrix_rows(
    meeting_id: str,
    hypotheses: dict[int, str],
    references: dict[str, str],
    elapsed_sec: dict[int, float],
) -> list[dict[str, object]]:
    """Tum headset x speaker eslesmelerini hesaplar."""
    rows: list[dict[str, object]] = []
    for headset_id, hypothesis in hypotheses.items():
        for speaker_id, reference in references.items():
            metrics = calculate_metrics(reference, hypothesis)
            rows.append(
                {
                    "meeting_id": meeting_id,
                    "headset_id": headset_id,
                    "speaker_ref": speaker_id,
                    "wer": round(metrics["wer"], 4),
                    "cer": round(metrics["cer"], 4),
                    "insertions": metrics["insertions"],
                    "deletions": metrics["deletions"],
                    "substitutions": metrics["substitutions"],
                    "hits": metrics["hits"],
                    "ref_words": metrics["ref_words"],
                    "hyp_words": metrics["hyp_words"],
                    "processing_time_sec": round(elapsed_sec[headset_id], 2),
                }
            )
    return rows


def save_hypothesis_checkpoint(
    meeting_id: str,
    headset_id: int,
    hypothesis: str,
) -> Path:
    """Her headset transkripsiyonunu ayri bir dosya olarak kaydeder."""
    out_dir = DATA_DIR / "hypotheses"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{meeting_id}.Headset-{headset_id}.txt"
    out_path.write_text(hypothesis, encoding="utf-8")
    return out_path


def print_summary(df: pd.DataFrame) -> None:
    """Matris ve en iyi eslesmeleri okunabilir sekilde yazdir."""
    print("\n" + "=" * 72)
    print("  HEADSET -> SPEAKER WER MATRISI")
    print("=" * 72)
    pivot = df.pivot(index="headset_id", columns="speaker_ref", values="wer").sort_index()
    print(pivot.to_string(float_format=lambda value: f"{value:.4f}"))

    print("\nEn dusuk WER eslesmeleri:")
    for headset_id, group in df.groupby("headset_id"):
        best = group.sort_values(["wer", "insertions", "deletions"]).iloc[0]
        print(
            f"  Headset-{headset_id} -> Speaker {best['speaker_ref']} "
            f"(WER={best['wer']:.4f}, I={int(best['insertions'])}, "
            f"D={int(best['deletions'])}, S={int(best['substitutions'])})"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AMI headset-channel <-> speaker-reference eslesme matrisi"
    )
    parser.add_argument("--meeting_id", required=True, help="Orn. ES2002b")
    parser.add_argument(
        "--channels",
        default="0,1,2,3",
        help="Virgulle ayrilmis headset listesi. Orn: 0 veya 0,2,3",
    )
    parser.add_argument("--model", default="large-v3", help="Whisper model adi")
    parser.add_argument("--beam_size", type=int, default=5, help="Beam search boyutu")
    parser.add_argument("--cpu_threads", type=int, default=8, help="CPU thread sayisi")
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Initial prompt kullanma",
    )
    parser.add_argument(
        "--output",
        help="Sonuc CSV dosya yolu. Varsayilan: data/ami_randomized/<meeting>_channel_reference_matrix.csv",
    )
    args = parser.parse_args()

    meeting_id = args.meeting_id.strip()
    if not meeting_id:
        raise SystemExit("meeting_id bos olamaz")
    try:
        selected_channels = parse_channels(args.channels)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"[START] Meeting: {meeting_id}", flush=True)
    print("=" * 72, flush=True)
    print("  AMI CHANNEL <-> REFERENCE MATRIX", flush=True)
    print("=" * 72, flush=True)
    print(f"  Meeting        : {meeting_id}", flush=True)
    print(f"  Channels       : {selected_channels}", flush=True)
    print(f"  Model          : {args.model}", flush=True)
    print(f"  Beam size      : {args.beam_size}", flush=True)
    print(f"  CPU threads    : {args.cpu_threads}", flush=True)
    print(f"  Initial prompt : {'OFF' if args.no_prompt else 'ON'}", flush=True)
    print("=" * 72, flush=True)

    print("\n[1/4] Headset kanallari hazirlaniyor...", flush=True)
    audio_paths: dict[int, Path] = {}
    for headset_id in selected_channels:
        audio_path = download_headset_audio(meeting_id, headset_id)
        if audio_path is not None:
            audio_paths[headset_id] = audio_path

    if len(audio_paths) != len(selected_channels):
        missing = sorted(set(selected_channels) - set(audio_paths))
        raise SystemExit(f"Eksik headset kanallari var: {missing}")

    print("\n[2/4] Speaker referanslari hazirlaniyor...", flush=True)
    xml_paths = download_speaker_references(meeting_id)
    references = prepare_reference_texts(meeting_id, xml_paths)
    if len(references) != len(SPEAKER_IDS):
        missing = sorted(set(SPEAKER_IDS) - set(references))
        raise SystemExit(f"Eksik speaker referanslari var: {missing}")

    default_output = DATA_DIR / f"{meeting_id}_channel_reference_matrix.csv"
    output_path = Path(args.output) if args.output else default_output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("[LOAD] Loading Faster-Whisper model...", flush=True)
    model = WhisperModel(
        args.model,
        device="cpu",
        compute_type="int8",
        cpu_threads=args.cpu_threads,
        num_workers=1,
    )
    print("[OK] Model loaded", flush=True)
    hypotheses: dict[int, str] = {}
    elapsed_sec: dict[int, float] = {}
    rows: list[dict[str, object]] = []

    for headset_id in sorted(audio_paths):
        print(f"\n  Transcribe: Headset-{headset_id}", flush=True)
        hypothesis, elapsed = transcribe_single_headset(
            model,
            audio_paths[headset_id],
            beam_size=args.beam_size,
            use_prompt=not args.no_prompt,
        )
        hypotheses[headset_id] = hypothesis
        elapsed_sec[headset_id] = elapsed
        hypothesis_path = save_hypothesis_checkpoint(meeting_id, headset_id, hypothesis)
        print(
            f"    kelime={len(hypothesis.split())} sure={elapsed:.1f}s "
            f"hyp={hypothesis_path.name}",
            flush=True,
        )

        rows.extend(
            build_matrix_rows(
                meeting_id,
                {headset_id: hypothesis},
                references,
                {headset_id: elapsed},
            )
        )
        partial_df = pd.DataFrame(rows).sort_values(["headset_id", "wer", "speaker_ref"])
        partial_df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"    partial CSV guncellendi: {output_path.name}", flush=True)

    print("\n[4/4] WER matrisi tamamlanıyor...", flush=True)
    result_df = pd.DataFrame(rows).sort_values(["headset_id", "wer", "speaker_ref"])
    result_df.to_csv(output_path, index=False, encoding="utf-8")

    print_summary(result_df)
    print(f"\nCSV kaydedildi: {output_path}", flush=True)


if __name__ == "__main__":
    main()

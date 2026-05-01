"""
leakage_detector.py
-------------------
Cross-channel audio leakage (crosstalk) tespiti ve filtreleme.

He & Whitehill (2025) "Cross-Speaker Context" kavramindan esinlenerek,
cok kanalli kayitlarda bir konusmacinin sessiz oldugu zaman dilimlerinde
kanalina sizan diger konusmacilarin seslerini tespit eder.

Algoritma: Cross-Channel Energy Muting
  - librosa ile her iki kanalin RMS enerjisini pencere bazli hesaplar
  - Eger Kanal A'daki enerji, Kanal B'deki enerjiye gore cok dusukse
    ve ayni zaman diliminde B'de aktif konusma varsa -> leakage

Kullanim:
    from src.services.leakage_detector import (
        detect_cross_talk_leakage,
        filter_leaked_segments,
        summarize_leakage,
    )

    mask = detect_cross_talk_leakage("ilgin.ogg", "merve.ogg")
    filtered = filter_leaked_segments(ilgin_segments, mask, sr=16000)
"""

import logging
import os
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger("meeting_analyzer.leakage_detector")

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False
    logger.warning("librosa yuklu degil. Leakage tespiti devre disi.")


@dataclass
class LeakageEvent:
    """Tespit edilen bir leakage olayi."""
    target_channel: str
    source_channel: str
    start_sec: float
    end_sec: float
    target_rms: float
    source_rms: float
    energy_ratio: float
    segment_text: str = ""


# ---------------------------------------------------------------------------
# Ana Algoritma: Cross-Channel Energy Muting
# ---------------------------------------------------------------------------

def detect_cross_talk_leakage(
    audio_target_path: str,
    audio_source_path: str,
    window_ms: int = 500,
    hop_ms: int = 250,
    energy_ratio_threshold: float = 0.15,
    sr: int = 16000,
) -> list[dict]:
    """
    Eger Kanal Target'daki enerji, Kanal Source'daki enerjinin
    belirli bir oraninin altindaysa VE Source'da o an konusma varsa,
    Target'taki ses "leakage" olarak isaretlenir.

    Args:
        audio_target_path: Leakage suphelisi kanal (ornegin Ilgin'in kanali)
        audio_source_path: Kaynak kanal (ornegin Merve'nin kanali)
        window_ms: Analiz pencere boyutu (ms)
        hop_ms: Pencere kayma miktari (ms)
        energy_ratio_threshold: target_rms/source_rms < bu deger ise leakage
        sr: Ornek orani (Hz)

    Returns:
        list[dict]: Her pencere icin {start, end, is_leakage, target_rms, source_rms, ratio}
    """
    if not HAS_LIBROSA:
        logger.error("librosa gerekli ama yuklu degil.")
        return []

    if not os.path.exists(audio_target_path):
        logger.error("Hedef ses dosyasi bulunamadi: %s", audio_target_path)
        return []
    if not os.path.exists(audio_source_path):
        logger.error("Kaynak ses dosyasi bulunamadi: %s", audio_source_path)
        return []

    y_target, _ = librosa.load(audio_target_path, sr=sr)
    y_source, _ = librosa.load(audio_source_path, sr=sr)

    window = int(sr * window_ms / 1000)
    hop = int(sr * hop_ms / 1000)

    # Uzunluklari esitle (kisa olani sifirla)
    max_len = max(len(y_target), len(y_source))
    if len(y_target) < max_len:
        y_target = np.pad(y_target, (0, max_len - len(y_target)))
    if len(y_source) < max_len:
        y_source = np.pad(y_source, (0, max_len - len(y_source)))

    frames = []
    for i in range(0, len(y_target) - window, hop):
        frame_target = y_target[i:i + window]
        frame_source = y_source[i:i + window]

        rms_target = float(np.sqrt(np.mean(frame_target ** 2)))
        rms_source = float(np.sqrt(np.mean(frame_source ** 2)))

        start_sec = i / sr
        end_sec = (i + window) / sr

        # Leakage tespiti:
        # Source'da enerji var VE Target'daki enerji Source'a gore cok dusuk
        is_leakage = False
        ratio = 0.0

        if rms_source > 0.001:  # Source'da minimum enerji var mi?
            ratio = rms_target / rms_source if rms_source > 0 else float("inf")
            # Target/Source < threshold ise leakage DEĞİL
            # Target/Source > threshold ama Target çok düşük -> leakage olabilir
            # Asıl mantık: Source güçlü, Target zayıf ama sıfır değil -> leakage
            if rms_target > 0.001 and ratio < energy_ratio_threshold:
                # Target'da ses var ama çok zayıf -> leakage olmayabilir, sessiz bölge
                is_leakage = False
            elif rms_target > 0.001 and rms_source > rms_target and ratio < (1.0 / energy_ratio_threshold):
                # Source çok güçlü, Target'da da bir miktar enerji var -> leakage şüphesi
                # Bu durumda Target'daki ses Source'dan sızma olabilir
                if rms_target < rms_source * energy_ratio_threshold:
                    is_leakage = True

        frames.append({
            "start": round(start_sec, 4),
            "end": round(end_sec, 4),
            "is_leakage": is_leakage,
            "target_rms": round(rms_target, 6),
            "source_rms": round(rms_source, 6),
            "ratio": round(ratio, 4),
        })

    leakage_count = sum(1 for f in frames if f["is_leakage"])
    total_count = len(frames)
    logger.info(
        "Leakage analizi: %d/%d frame leakage (%%.1f%%)",
        leakage_count,
        total_count,
        (leakage_count / total_count * 100) if total_count > 0 else 0,
    )

    return frames


def check_segment_leakage(
    segment_start: float,
    segment_end: float,
    leakage_frames: list[dict],
    leakage_coverage_threshold: float = 0.50,
) -> bool:
    """
    Bir transkripsiyon segmentinin leakage olup olmadigini kontrol eder.

    Segment suresinin %50+'sinda leakage=True ise, bu segment
    "suspected leakage" olarak isaretlenir.

    Args:
        segment_start: Segment baslangic zamani (saniye)
        segment_end: Segment bitis zamani (saniye)
        leakage_frames: detect_cross_talk_leakage() ciktisi
        leakage_coverage_threshold: Segment suresinin ne kadari
                                    leakage olmali (0.0-1.0)

    Returns:
        True ise segment leakage suphelisi
    """
    if not leakage_frames:
        return False

    overlapping_frames = 0
    leakage_frames_count = 0

    for frame in leakage_frames:
        # Frame segment ile ortusüyor mu?
        overlap = min(segment_end, frame["end"]) - max(segment_start, frame["start"])
        if overlap > 0:
            overlapping_frames += 1
            if frame["is_leakage"]:
                leakage_frames_count += 1

    if overlapping_frames == 0:
        return False

    coverage = leakage_frames_count / overlapping_frames
    return coverage >= leakage_coverage_threshold


def filter_leaked_segments(
    segments: list[dict],
    leakage_frames: list[dict],
    leakage_coverage_threshold: float = 0.50,
) -> tuple[list[dict], list[dict]]:
    """
    Leakage olarak isaretlenen segmentleri filtreler.

    Args:
        segments: Whisper ciktisi segment listesi
                  [{"start": ..., "end": ..., "text": ...}, ...]
        leakage_frames: detect_cross_talk_leakage() ciktisi
        leakage_coverage_threshold: Leakage kapsama esigi

    Returns:
        (temiz_segmentler, leakage_segmentler)
    """
    clean = []
    leaked = []

    for seg in segments:
        seg_start = seg.get("start", 0)
        seg_end = seg.get("end", 0)

        if check_segment_leakage(
            seg_start, seg_end, leakage_frames, leakage_coverage_threshold
        ):
            leaked.append(seg)
        else:
            clean.append(seg)

    return clean, leaked


def summarize_leakage(leakage_frames: list[dict]) -> dict:
    """
    Leakage frame analizinin istatistiksel ozetini cikarir.
    """
    if not leakage_frames:
        return {
            "total_frames": 0,
            "leakage_frames": 0,
            "leakage_ratio": 0.0,
            "total_duration_sec": 0.0,
            "leakage_duration_sec": 0.0,
        }

    total = len(leakage_frames)
    leakage_count = sum(1 for f in leakage_frames if f["is_leakage"])
    frame_duration = leakage_frames[0]["end"] - leakage_frames[0]["start"] if total > 0 else 0

    return {
        "total_frames": total,
        "leakage_frames": leakage_count,
        "leakage_ratio": round(leakage_count / total, 4) if total > 0 else 0.0,
        "total_duration_sec": round(total * frame_duration, 2),
        "leakage_duration_sec": round(leakage_count * frame_duration, 2),
    }


# ---------------------------------------------------------------------------
# Coklu Kanal Analizi (N konusmaci)
# ---------------------------------------------------------------------------

def detect_leakage_multichannel(
    audio_paths: dict[str, str],
    **kwargs,
) -> dict[str, list[dict]]:
    """
    N kanalli kayitlarda her kanal icin diger tum kanallara karsi
    leakage analizi yapar.

    Args:
        audio_paths: { "spk_0": "/path/to/audio.ogg", ... }
        **kwargs: detect_cross_talk_leakage icin ek parametreler

    Returns:
        { "spk_0": [frame dicts...], "spk_1": [...], ... }
        Her kanalin en kotu (en fazla leakage) kaynak ile analizi
    """
    if not HAS_LIBROSA:
        return {}

    channels = list(audio_paths.keys())
    results = {}

    for target_ch in channels:
        worst_leakage_ratio = 0.0
        worst_frames = []

        for source_ch in channels:
            if source_ch == target_ch:
                continue

            frames = detect_cross_talk_leakage(
                audio_paths[target_ch],
                audio_paths[source_ch],
                **kwargs,
            )

            if frames:
                ratio = sum(1 for f in frames if f["is_leakage"]) / len(frames)
                if ratio > worst_leakage_ratio:
                    worst_leakage_ratio = ratio
                    worst_frames = frames

        results[target_ch] = worst_frames

    return results

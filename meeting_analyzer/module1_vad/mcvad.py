"""
mcvad.py
--------
Multi-channel VAD orchestration and segment generation.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import config
from .energy_vad import EnergyVAD, VADResult

logger = logging.getLogger(config.LOGGER_NAME)


@dataclass
class Segment:
    speaker: str
    start: float
    end: float
    type: str
    speakers: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker,
            "start": round(self.start, 4),
            "end": round(self.end, 4),
            "duration": round(self.duration, 4),
            "type": self.type,
            "speakers": self.speakers,
        }


class MultiChannelVAD:
    """Run per-channel VAD, then merge channels into single/overlap segments."""

    def __init__(
        self,
        sample_rate: int = config.SAMPLE_RATE,
        min_segment_ms: int = config.MIN_SEGMENT_MS,
        frame_length_ms: int = config.FRAME_LENGTH_MS,
        hop_length_ms: int = config.HOP_LENGTH_MS,
        threshold_multiplier: float = config.ADAPTIVE_THRESHOLD_MULTIPLIER,
        adaptive_window_sec: float = config.ADAPTIVE_WINDOW_SECONDS,
        bleed_ratio: float = config.BLEED_RATIO,
        dominant_ratio: float = config.DOMINANT_RATIO,
        use_spectral: bool = True,
        sfm_threshold: float = config.SPECTRAL_FLATNESS_THRESHOLD,
        local_weight: float = 0.7,
        global_weight: float = 0.3,
        use_pyannote: bool = False,
        hf_token: str = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.min_segment_ms = min_segment_ms
        self.bleed_ratio = bleed_ratio
        self.dominant_ratio = dominant_ratio

        if use_pyannote:
            from .pyannote_vad import PyannoteVAD

            self.vad = PyannoteVAD(sample_rate=sample_rate, hf_token=hf_token)
            logger.info("MultiChannelVAD: using PyannoteVAD.")
        else:
            self.vad = EnergyVAD(
                sample_rate=sample_rate,
                frame_length_ms=frame_length_ms,
                hop_length_ms=hop_length_ms,
                threshold_multiplier=threshold_multiplier,
                adaptive_window_sec=adaptive_window_sec,
                use_spectral=use_spectral,
                sfm_threshold=sfm_threshold,
                local_weight=local_weight,
                global_weight=global_weight,
            )
            logger.info("MultiChannelVAD: using EnergyVAD.")

    def get_activity_matrix(
        self,
        channel_audio_dict: Dict[str, np.ndarray],
    ) -> Tuple[np.ndarray, List[str], np.ndarray]:
        if not channel_audio_dict:
            raise ValueError("channel_audio_dict boş olamaz.")

        speaker_ids = list(channel_audio_dict.keys())
        vad_results: Dict[str, VADResult] = {}
        for speaker_id, audio in channel_audio_dict.items():
            vad_results[speaker_id] = self.vad.detect(audio, self.sample_rate)

        n_frames = min(len(result.frame_activity) for result in vad_results.values())
        frame_times = next(iter(vad_results.values())).frame_times[:n_frames]

        activity_matrix = np.zeros((len(speaker_ids), n_frames), dtype=bool)
        energy_matrix = np.zeros((len(speaker_ids), n_frames), dtype=np.float32)

        for idx, speaker_id in enumerate(speaker_ids):
            result = vad_results[speaker_id]
            activity_matrix[idx, :] = result.frame_activity[:n_frames]
            energy_matrix[idx, :] = result.frame_energies[:n_frames]

        activity_matrix = self._apply_bleed_suppression(activity_matrix, energy_matrix)
        activity_matrix = self._apply_dominant_only(activity_matrix, energy_matrix)

        return activity_matrix, speaker_ids, frame_times

    def process(self, channel_audio_dict: Dict[str, np.ndarray]) -> List[dict]:
        activity_matrix, speaker_ids, frame_times = self.get_activity_matrix(channel_audio_dict)
        raw_segments = self._activity_to_segments(activity_matrix, speaker_ids, frame_times)
        merged_segments = self._merge_short_segments(raw_segments)
        return [segment.to_dict() for segment in merged_segments]

    def _apply_bleed_suppression(
        self,
        activity_matrix: np.ndarray,
        energy_matrix: np.ndarray,
    ) -> np.ndarray:
        if self.bleed_ratio <= 0:
            return activity_matrix

        result = activity_matrix.copy()
        for frame_idx in range(result.shape[1]):
            active_indices = np.flatnonzero(result[:, frame_idx])
            if active_indices.size == 0:
                continue

            max_energy = float(np.max(energy_matrix[:, frame_idx]))
            if max_energy < config.GLOBAL_SPEECH_FLOOR:
                result[:, frame_idx] = False
                continue

            cutoff = self.bleed_ratio * max_energy
            for channel_idx in active_indices:
                if float(energy_matrix[channel_idx, frame_idx]) < cutoff:
                    result[channel_idx, frame_idx] = False

        return result

    def _apply_dominant_only(
        self,
        activity_matrix: np.ndarray,
        energy_matrix: np.ndarray,
    ) -> np.ndarray:
        if self.dominant_ratio <= 0:
            return activity_matrix

        result = activity_matrix.copy()
        for frame_idx in range(result.shape[1]):
            active_indices = np.flatnonzero(result[:, frame_idx])
            if active_indices.size < 2:
                continue

            active_energies = energy_matrix[active_indices, frame_idx]
            order = np.argsort(active_energies)[::-1]
            top_idx = active_indices[order[0]]
            top_energy = float(active_energies[order[0]])
            second_energy = float(active_energies[order[1]])

            if second_energy <= 0 or top_energy / second_energy > self.dominant_ratio:
                result[:, frame_idx] = False
                result[top_idx, frame_idx] = True

        return result

    def _activity_to_segments(
        self,
        activity_matrix: np.ndarray,
        speaker_ids: List[str],
        frame_times: np.ndarray,
    ) -> List[Segment]:
        hop_sec = self.vad.hop_duration
        segments: List[Segment] = []

        prev_label: Optional[str] = None
        prev_speakers: List[str] = []
        seg_start = 0.0

        n_frames = activity_matrix.shape[1]
        for frame_idx in range(n_frames):
            active_mask = activity_matrix[:, frame_idx]
            active_speakers = [speaker_ids[i] for i in range(len(speaker_ids)) if active_mask[i]]

            if len(active_speakers) == 0:
                current_label = None
                current_speakers: List[str] = []
            elif len(active_speakers) == 1:
                current_label = active_speakers[0]
                current_speakers = active_speakers
            else:
                current_label = "overlap"
                current_speakers = sorted(active_speakers)

            if current_label != prev_label or current_speakers != prev_speakers:
                if prev_label is not None:
                    seg_end = frame_times[frame_idx] if frame_idx > 0 else hop_sec
                    segments.append(
                        Segment(
                            speaker=prev_label,
                            start=seg_start,
                            end=seg_end,
                            type="overlap" if prev_label == "overlap" else "single",
                            speakers=list(prev_speakers),
                        )
                    )
                seg_start = frame_times[frame_idx]
                prev_label = current_label
                prev_speakers = list(current_speakers)

        if prev_label is not None and n_frames > 0:
            segments.append(
                Segment(
                    speaker=prev_label,
                    start=seg_start,
                    end=frame_times[-1] + hop_sec,
                    type="overlap" if prev_label == "overlap" else "single",
                    speakers=list(prev_speakers),
                )
            )

        return segments

    def _merge_short_segments(self, segments: List[Segment]) -> List[Segment]:
        if not segments:
            return []

        min_duration = self.min_segment_ms / 1000.0
        merged: List[Segment] = []

        for segment in segments:
            if segment.duration >= min_duration:
                merged.append(segment)
                continue

            if merged:
                merged[-1] = Segment(
                    speaker=merged[-1].speaker,
                    start=merged[-1].start,
                    end=segment.end,
                    type=merged[-1].type,
                    speakers=merged[-1].speakers,
                )

        return merged

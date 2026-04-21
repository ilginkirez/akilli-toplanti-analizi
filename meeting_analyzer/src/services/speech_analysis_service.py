import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from module1_vad import AudioStandardizer, MultiChannelVAD, RTTMWriter, config

from .ai_analysis_service import ai_analysis_service
from .session_store import session_store

logger = logging.getLogger("meeting_analyzer.speech_analysis")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _samples_from_ms(value_ms: int, sample_rate: int) -> int:
    return max(0, int(round((value_ms / 1000.0) * sample_rate)))


@dataclass
class AudioTrack:
    participant_id: str
    display_name: str
    stream_id: str
    connection_id: Optional[str]
    relative_path: str
    absolute_path: Path
    start_time_offset_ms: int
    end_time_offset_ms: Optional[int]
    has_audio: bool


@dataclass
class LoadedAudioTrack(AudioTrack):
    audio: np.ndarray
    expected_duration_ms: int


class SpeechAnalysisError(Exception):
    pass


class SpeechAnalysisService:
    def __init__(
        self,
        recordings_dir: Optional[str] = None,
    ) -> None:
        self.recordings_dir = Path(recordings_dir or session_store.recordings_dir)
        self.standardizer = AudioStandardizer()
        self.sample_rate = config.SAMPLE_RATE

    def analyze_session(self, session_id: str) -> Dict[str, Any]:
        session = session_store.load_session(session_id)
        recording = session.get("recording", {})
        analysis_started = time.perf_counter()

        session_store.update_speech_analysis(
            session_id,
            {
                "status": "processing",
                "generated_at": None,
                "error": None,
            },
        )

        try:
            tracks = self._collect_tracks(session)
            if not tracks:
                raise SpeechAnalysisError(
                    "Konusma analizi icin ses track'i bulunamadi."
                )

            loaded_tracks = self._load_tracks(tracks)
            aligned_audio = self._align_tracks(loaded_tracks)

            total_samples = max((len(audio) for audio in aligned_audio.values()), default=0)
            recording_duration_sec = round(total_samples / self.sample_rate, 4) if total_samples else 0.0
            if total_samples == 0:
                raw_segments: List[dict] = []
            else:
                raw_segments = MultiChannelVAD(sample_rate=self.sample_rate).process(aligned_audio)
            processing_duration_sec = round(time.perf_counter() - analysis_started, 4)

            analysis_dir = self.recordings_dir / session_id / "analysis"
            analysis_dir.mkdir(parents=True, exist_ok=True)

            recording_started_at = recording.get("started_at")
            analysis_parameters = self._build_analysis_parameters()
            segment_entries = self._build_segment_entries(
                raw_segments=raw_segments,
                session=session,
                recording_started_at=recording_started_at,
            )
            metrics = self._build_metrics(
                raw_segments=raw_segments,
                recording_duration_sec=recording_duration_sec,
                processing_duration_sec=processing_duration_sec,
            )
            summary = self._build_summary(
                segments=segment_entries,
                session=session,
                metrics=metrics,
            )

            rttm_rel_path = None
            if raw_segments:
                rttm_path = analysis_dir / "speakers.rttm"
                RTTMWriter(recording_id=session_id).write(
                    raw_segments,
                    rttm_path,
                    recording_id=session_id,
                )
                rttm_rel_path = rttm_path.relative_to(self.recordings_dir).as_posix()

            source_tracks = [
                {
                    "participant_id": track.participant_id,
                    "display_name": track.display_name,
                    "stream_id": track.stream_id,
                    "connection_id": track.connection_id,
                    "file_path": track.relative_path,
                    "start_time_offset_ms": track.start_time_offset_ms,
                    "end_time_offset_ms": track.end_time_offset_ms,
                    "has_audio": track.has_audio,
                }
                for track in tracks
            ]

            payload = {
                "session_id": session_id,
                "status": "ready",
                "generated_at": _utc_now_iso(),
                "timebase": "recording",
                "recording_started_at": recording_started_at,
                "segments_path": None,
                "rttm_path": rttm_rel_path,
                "segments": segment_entries,
                "summary": summary,
                "metrics": metrics,
                "analysis_parameters": analysis_parameters,
                "source_tracks": source_tracks,
                "error": None,
            }

            output_path = analysis_dir / "speech_segments.json"
            output_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            payload["segments_path"] = output_path.relative_to(self.recordings_dir).as_posix()
            output_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            session_store.update_speech_analysis(session_id, payload)
            try:
                ai_analysis_service.analyze_session(session_id)
            except Exception:
                logger.exception(
                    "[session_id=%s] AI analizi speech analysis sonrasi basarisiz",
                    session_id,
                )
            logger.info(
                "[session_id=%s] Konusma analizi tamamlandi: %d segment",
                session_id,
                len(segment_entries),
            )
            return payload
        except Exception as exc:
            error_payload = {
                "status": "failed",
                "generated_at": _utc_now_iso(),
                "error": str(exc),
            }
            session_store.update_speech_analysis(session_id, error_payload)
            logger.exception(
                "[session_id=%s] Konusma analizi basarisiz",
                session_id,
            )
            raise SpeechAnalysisError(str(exc)) from exc

    def _collect_tracks(self, session: Dict[str, Any]) -> List[AudioTrack]:
        tracks: List[AudioTrack] = []

        for participant in session.get("participants", []):
            participant_id = participant.get("participant_id")
            if not participant_id:
                continue

            display_name = participant.get("display_name") or participant_id
            for item in participant.get("recording_files", []):
                if not item.get("has_audio"):
                    continue

                relative_path = item.get("file_path")
                if not relative_path:
                    continue

                absolute_path = self.recordings_dir / relative_path
                if not absolute_path.exists():
                    logger.warning(
                        "Kayit dosyasi bulunamadi, atlanacak: %s",
                        absolute_path,
                    )
                    continue

                start_offset_ms = int(item.get("start_time_offset_ms") or 0)
                end_offset_ms = item.get("end_time_offset_ms")
                tracks.append(
                    AudioTrack(
                        participant_id=participant_id,
                        display_name=display_name,
                        stream_id=item.get("stream_id") or participant.get("stream_id") or participant_id,
                        connection_id=item.get("connection_id") or participant.get("connection_id"),
                        relative_path=relative_path,
                        absolute_path=absolute_path,
                        start_time_offset_ms=start_offset_ms,
                        end_time_offset_ms=int(end_offset_ms) if end_offset_ms is not None else None,
                        has_audio=bool(item.get("has_audio")),
                    )
                )

        return tracks

    def _load_tracks(self, tracks: List[AudioTrack]) -> List[LoadedAudioTrack]:
        loaded_tracks: List[LoadedAudioTrack] = []

        for track in tracks:
            audio = self.standardizer.load_and_standardize(track.absolute_path)
            if audio.ndim != 1:
                audio = np.asarray(audio).reshape(-1)

            expected_duration_ms = int(round((len(audio) / self.sample_rate) * 1000))
            if (
                track.end_time_offset_ms is not None
                and track.end_time_offset_ms > track.start_time_offset_ms
            ):
                expected_duration_ms = max(
                    expected_duration_ms,
                    track.end_time_offset_ms - track.start_time_offset_ms,
                )

            loaded_tracks.append(
                LoadedAudioTrack(
                    **track.__dict__,
                    audio=np.asarray(audio, dtype=np.float32),
                    expected_duration_ms=expected_duration_ms,
                )
            )

        return loaded_tracks

    def _align_tracks(
        self,
        tracks: List[LoadedAudioTrack],
    ) -> Dict[str, np.ndarray]:
        if not tracks:
            return {}

        prepared_tracks: List[LoadedAudioTrack] = []
        total_samples = 0

        for track in tracks:
            expected_samples = _samples_from_ms(track.expected_duration_ms, self.sample_rate)
            audio = track.audio
            if expected_samples > len(audio):
                audio = np.pad(audio, (0, expected_samples - len(audio)))
            elif expected_samples > 0 and expected_samples < len(audio):
                audio = audio[:expected_samples]

            start_samples = _samples_from_ms(track.start_time_offset_ms, self.sample_rate)
            total_samples = max(total_samples, start_samples + len(audio))
            prepared_tracks.append(
                LoadedAudioTrack(
                    **{
                        **track.__dict__,
                        "audio": audio,
                    }
                )
            )

        aligned: Dict[str, np.ndarray] = {}
        for track in prepared_tracks:
            channel = aligned.setdefault(
                track.participant_id,
                np.zeros(total_samples, dtype=np.float32),
            )
            start = _samples_from_ms(track.start_time_offset_ms, self.sample_rate)
            end = min(start + len(track.audio), total_samples)
            if end <= start:
                continue

            existing = channel[start:end]
            incoming = track.audio[: end - start]
            stronger = np.abs(incoming) > np.abs(existing)
            existing[stronger] = incoming[stronger]
            channel[start:end] = existing

        return aligned

    def _build_segment_entries(
        self,
        raw_segments: List[dict],
        session: Dict[str, Any],
        recording_started_at: Optional[str],
    ) -> List[Dict[str, Any]]:
        participants_by_id = {
            item.get("participant_id"): item
            for item in session.get("participants", [])
            if item.get("participant_id")
        }
        recording_start = _parse_iso_timestamp(recording_started_at)

        entries: List[Dict[str, Any]] = []
        for index, segment in enumerate(raw_segments, start=1):
            start_sec = round(float(segment.get("start", 0.0)), 4)
            end_sec = round(float(segment.get("end", 0.0)), 4)
            duration_sec = round(max(0.0, end_sec - start_sec), 4)
            speaker_ids = segment.get("speakers") or []

            participants = []
            if segment.get("type") == "single":
                speaker_id = segment.get("speaker")
                participant = participants_by_id.get(speaker_id, {})
                participants = [
                    {
                        "participant_id": speaker_id,
                        "display_name": participant.get("display_name") or speaker_id,
                    }
                ]
            else:
                for speaker_id in speaker_ids:
                    participant = participants_by_id.get(speaker_id, {})
                    participants.append(
                        {
                            "participant_id": speaker_id,
                            "display_name": participant.get("display_name") or speaker_id,
                        }
                    )

            entry: Dict[str, Any] = {
                "segment_id": index,
                "type": segment.get("type", "single"),
                "overlap": segment.get("type") == "overlap",
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": duration_sec,
                "participants": participants,
            }

            if segment.get("type") == "single" and participants:
                entry["participant_id"] = participants[0]["participant_id"]
                entry["display_name"] = participants[0]["display_name"]

            if recording_start is not None:
                entry["start_at"] = (
                    recording_start + timedelta(seconds=start_sec)
                ).isoformat()
                entry["end_at"] = (
                    recording_start + timedelta(seconds=end_sec)
                ).isoformat()

            entries.append(entry)

        return entries

    def _build_summary(
        self,
        segments: List[Dict[str, Any]],
        session: Dict[str, Any],
        metrics: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        totals: Dict[str, Dict[str, Any]] = {}
        metrics = metrics or {}
        recording_duration_sec = float(metrics.get("recording_duration_sec") or 0.0)
        active_speech_sec = float(metrics.get("active_speech_sec") or 0.0)

        for participant in session.get("participants", []):
            participant_id = participant.get("participant_id")
            if not participant_id:
                continue
            totals[participant_id] = {
                "participant_id": participant_id,
                "display_name": participant.get("display_name") or participant_id,
                "segment_count": 0,
                "single_segment_count": 0,
                "overlap_segment_count": 0,
                "total_speaking_sec": 0.0,
                "overlap_involved_sec": 0.0,
                "first_spoken_sec": None,
                "last_spoken_sec": None,
            }

        for segment in segments:
            for participant in segment.get("participants", []):
                participant_id = participant.get("participant_id")
                if participant_id not in totals:
                    totals[participant_id] = {
                        "participant_id": participant_id,
                        "display_name": participant.get("display_name") or participant_id,
                        "segment_count": 0,
                        "single_segment_count": 0,
                        "overlap_segment_count": 0,
                        "total_speaking_sec": 0.0,
                        "overlap_involved_sec": 0.0,
                        "first_spoken_sec": None,
                        "last_spoken_sec": None,
                    }

                summary = totals[participant_id]
                summary["segment_count"] += 1
                if segment.get("overlap"):
                    summary["overlap_segment_count"] += 1
                else:
                    summary["single_segment_count"] += 1

                duration_sec = float(segment.get("duration_sec", 0.0))
                summary["total_speaking_sec"] = round(
                    summary["total_speaking_sec"] + duration_sec,
                    4,
                )
                if segment.get("overlap"):
                    summary["overlap_involved_sec"] = round(
                        summary["overlap_involved_sec"] + duration_sec,
                        4,
                    )

                start_sec = float(segment.get("start_sec", 0.0))
                end_sec = float(segment.get("end_sec", 0.0))
                if summary["first_spoken_sec"] is None or start_sec < summary["first_spoken_sec"]:
                    summary["first_spoken_sec"] = round(start_sec, 4)
                if summary["last_spoken_sec"] is None or end_sec > summary["last_spoken_sec"]:
                    summary["last_spoken_sec"] = round(end_sec, 4)

        for summary in totals.values():
            duration = float(summary.get("total_speaking_sec") or 0.0)
            overlap_involved_sec = float(summary.get("overlap_involved_sec") or 0.0)
            summary["speaking_percentage_of_recording"] = self._percentage(
                duration,
                recording_duration_sec,
            )
            summary["speaking_percentage_of_active_speech"] = self._percentage(
                duration,
                active_speech_sec,
            )
            summary["overlap_percentage_of_speaking"] = self._percentage(
                overlap_involved_sec,
                duration,
            )

        return sorted(totals.values(), key=lambda item: item["display_name"])

    @staticmethod
    def _percentage(value: float, total: float) -> float:
        if total <= 0:
            return 0.0
        return round((value / total) * 100.0, 2)

    def _build_analysis_parameters(self) -> Dict[str, Any]:
        return {
            "vad_backend": "energy",
            "sample_rate_hz": self.sample_rate,
            "frame_length_ms": config.FRAME_LENGTH_MS,
            "hop_length_ms": config.HOP_LENGTH_MS,
            "adaptive_window_sec": config.ADAPTIVE_WINDOW_SECONDS,
            "threshold_multiplier": config.ADAPTIVE_THRESHOLD_MULTIPLIER,
            "noise_floor": config.NOISE_FLOOR,
            "global_speech_floor": config.GLOBAL_SPEECH_FLOOR,
            "use_spectral": True,
            "spectral_flatness_threshold": config.SPECTRAL_FLATNESS_THRESHOLD,
            "bleed_ratio": config.BLEED_RATIO,
            "dominant_ratio": config.DOMINANT_RATIO,
            "min_segment_ms": config.MIN_SEGMENT_MS,
        }

    def _build_metrics(
        self,
        raw_segments: List[dict],
        recording_duration_sec: float,
        processing_duration_sec: float,
    ) -> Dict[str, Any]:
        durations = [
            max(0.0, float(segment.get("end", 0.0)) - float(segment.get("start", 0.0)))
            for segment in raw_segments
        ]
        active_speech_sec = round(sum(durations), 4)
        overlap_duration_sec = round(
            sum(
                max(0.0, float(segment.get("end", 0.0)) - float(segment.get("start", 0.0)))
                for segment in raw_segments
                if segment.get("type") == "overlap"
            ),
            4,
        )
        single_speech_sec = round(max(active_speech_sec - overlap_duration_sec, 0.0), 4)
        silence_duration_sec = round(max(recording_duration_sec - active_speech_sec, 0.0), 4)
        single_segment_count = sum(1 for segment in raw_segments if segment.get("type") != "overlap")
        overlap_segment_count = sum(1 for segment in raw_segments if segment.get("type") == "overlap")

        average_segment_duration_sec = round(float(np.mean(durations)), 4) if durations else 0.0
        median_segment_duration_sec = round(float(np.median(durations)), 4) if durations else 0.0
        segment_density_per_min = round(
            (len(raw_segments) / (recording_duration_sec / 60.0)),
            4,
        ) if recording_duration_sec > 0 else 0.0
        real_time_factor = round(
            (processing_duration_sec / recording_duration_sec),
            4,
        ) if recording_duration_sec > 0 else 0.0
        processing_speed_x = round(
            (recording_duration_sec / processing_duration_sec),
            4,
        ) if processing_duration_sec > 0 else 0.0

        return {
            "recording_duration_sec": round(recording_duration_sec, 4),
            "processing_duration_sec": round(processing_duration_sec, 4),
            "real_time_factor": real_time_factor,
            "processing_speed_x": processing_speed_x,
            "active_speech_sec": active_speech_sec,
            "active_speech_percentage": self._percentage(active_speech_sec, recording_duration_sec),
            "single_speech_sec": single_speech_sec,
            "single_speech_percentage": self._percentage(single_speech_sec, recording_duration_sec),
            "overlap_duration_sec": overlap_duration_sec,
            "overlap_percentage_of_recording": self._percentage(
                overlap_duration_sec,
                recording_duration_sec,
            ),
            "overlap_percentage_of_active_speech": self._percentage(
                overlap_duration_sec,
                active_speech_sec,
            ),
            "silence_duration_sec": silence_duration_sec,
            "silence_percentage": self._percentage(silence_duration_sec, recording_duration_sec),
            "segment_count": len(raw_segments),
            "single_segment_count": single_segment_count,
            "overlap_segment_count": overlap_segment_count,
            "segment_density_per_min": segment_density_per_min,
            "average_segment_duration_sec": average_segment_duration_sec,
            "median_segment_duration_sec": median_segment_duration_sec,
        }


speech_analysis_service = SpeechAnalysisService()

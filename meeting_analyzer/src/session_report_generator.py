"""
session_report_generator.py
---------------------------
Oturum sonuç raporu üretici modülü.

Oturum bitiminde aşağıdaki bilgileri içeren JSON raporu üretir:
    - session_id, start_time, end_time, duration_sec
    - participants
    - total_speaking_time (katılımcı bazlı)
    - overlap_duration_sec, overlap_percentage
    - der_score
    - rttm_path, video_path, audio_tracks
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("meeting_analyzer.report")


class SessionReportGenerator:
    """
    Oturum sonuç raporu üreten sınıf.

    MultiChannelVAD segment listesinden istatistikleri hesaplar
    ve standart JSON rapor formatında çıktı üretir.

    Attributes:
        output_dir : Rapor dosyalarının yazılacağı dizin.
    """

    def __init__(self, output_dir: Optional[str] = None) -> None:
        """
        SessionReportGenerator örneği oluşturur.

        Args:
            output_dir : Rapor çıktı dizini. None ise "./recordings" kullanılır.
        """
        self.output_dir = Path(output_dir or "./recordings")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "SessionReportGenerator başlatıldı: output_dir=%s",
            self.output_dir,
        )

    # ------------------------------------------------------------------
    # Ana API
    # ------------------------------------------------------------------

    def generate(
        self,
        session_id: str,
        base_timestamp: float,
        participants: List[str],
        segments: List[dict],
        rttm_path: Optional[str] = None,
        video_path: Optional[str] = None,
        audio_files: Optional[Dict[str, str]] = None,
        errors: Optional[List[str]] = None,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Oturum sonuç raporu üretir ve JSON olarak kaydeder.

        Args:
            session_id     : Oturum kimliği.
            base_timestamp : Pipeline başlangıç zamanı (Unix epoch).
            participants   : Katılımcı adları.
            segments       : MultiChannelVAD.process() çıktısı.
            rttm_path      : RTTM dosya yolu.
            video_path     : Video dosya yolu.
            audio_files    : {participant: audio_file_path} sözlüğü.
            errors         : Oluşan hata listesi.
            output_path    : Rapor dosya yolu. None ise otomatik oluşturulur.

        Returns:
            Rapor sözlüğü (JSON ile aynı içerik).
        """
        end_timestamp = time.time()
        duration_sec = end_timestamp - base_timestamp

        # Konuşma süreleri
        speaking_times = self._calculate_speaking_times(segments, participants)

        # Overlap süreleri
        overlap_duration = self._calculate_overlap_duration(segments)
        overlap_percentage = (
            (overlap_duration / duration_sec * 100.0) if duration_sec > 0 else 0.0
        )

        # DER skoru (referans RTTM yoksa 0.0)
        der_score = 0.0

        # ISO 8601 zaman damgaları
        start_time_iso = datetime.fromtimestamp(
            base_timestamp, tz=timezone.utc
        ).isoformat()
        end_time_iso = datetime.fromtimestamp(
            end_timestamp, tz=timezone.utc
        ).isoformat()

        # Rapor sözlüğü
        report: Dict[str, Any] = {
            "session_id": session_id,
            "start_time": start_time_iso,
            "end_time": end_time_iso,
            "duration_sec": round(duration_sec, 2),
            "participants": participants,
            "total_speaking_time": {
                name: round(dur, 2) for name, dur in speaking_times.items()
            },
            "overlap_duration_sec": round(overlap_duration, 2),
            "overlap_percentage": round(overlap_percentage, 2),
            "der_score": der_score,
            "rttm_path": rttm_path or "",
            "video_path": video_path or "",
            "audio_tracks": audio_files or {},
        }

        # Hata bilgisi varsa ekle
        if errors:
            report["errors"] = errors
            report["status"] = "completed_with_errors"
        else:
            report["status"] = "completed"

        # JSON dosyası olarak kaydet
        report_file = Path(
            output_path
            or str(self.output_dir / session_id / f"{session_id}_report.json")
        )
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with report_file.open("w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)

        report["report_path"] = str(report_file)

        logger.info(
            "[session_id=%s] Rapor üretildi: %s (duration=%.1fs, "
            "segments=%d, overlap=%.1f%%)",
            session_id,
            report_file,
            duration_sec,
            len(segments),
            overlap_percentage,
        )

        return report

    # ------------------------------------------------------------------
    # Hesaplama Yardımcıları
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_speaking_times(
        segments: List[dict],
        participants: List[str],
    ) -> Dict[str, float]:
        """
        Her katılımcının toplam konuşma süresini hesaplar.

        Overlap segmentlerinde tüm aktif konuşmacıların süreleri artar.

        Args:
            segments     : Segment listesi.
            participants : Katılımcı adları.

        Returns:
            {participant_name: total_speaking_seconds} sözlüğü.
        """
        speaking_times: Dict[str, float] = {name: 0.0 for name in participants}

        for seg in segments:
            duration = float(seg.get("end", 0)) - float(seg.get("start", 0))
            if duration <= 0:
                continue

            seg_type = seg.get("type", "single")

            if seg_type == "overlap":
                # Overlap segmentinde tüm aktif konuşmacılar
                speakers = seg.get("speakers", [])
                for spk in speakers:
                    if spk in speaking_times:
                        speaking_times[spk] += duration
            elif seg_type == "single":
                speaker = seg.get("speaker", "")
                if speaker in speaking_times:
                    speaking_times[speaker] += duration

        return speaking_times

    @staticmethod
    def _calculate_overlap_duration(segments: List[dict]) -> float:
        """
        Toplam overlap süresini hesaplar.

        Args:
            segments : Segment listesi.

        Returns:
            Overlap süresi (saniye).
        """
        total_overlap = 0.0

        for seg in segments:
            if seg.get("type") == "overlap":
                duration = float(seg.get("end", 0)) - float(seg.get("start", 0))
                if duration > 0:
                    total_overlap += duration

        return total_overlap

    @staticmethod
    def calculate_vad_metrics(
        hypothesis_segments: List[dict],
        reference_segments: List[dict],
        total_duration: float,
        resolution_ms: int = 10,
    ) -> Dict[str, float]:
        """
        Referans segmentler varsa frame-bazlı VAD metriklerini hesaplar.

        Bu hesap konuşma/konuşmama ayrımı yapar; konuşmacı kimliğini dikkate
        almaz. Böylece klasik VAD literatüründe kullanılan precision, recall,
        F1, false alarm ve miss rate benzeri ölçütler elde edilir.

        Args:
            hypothesis_segments : Sistem çıktısı segmentler.
            reference_segments  : Referans konuşma segmentleri.
            total_duration      : Toplam zaman ekseni (saniye).
            resolution_ms       : Frame çözünürlüğü.

        Returns:
            Hesaplanan metrikleri içeren sözlük.
        """
        if total_duration <= 0 or resolution_ms <= 0:
            return {
                "resolution_ms": float(resolution_ms),
                "tp": 0.0,
                "fp": 0.0,
                "fn": 0.0,
                "tn": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "accuracy": 0.0,
                "false_alarm_rate": 0.0,
                "miss_rate": 0.0,
                "reference_speech_ratio": 0.0,
                "hypothesis_speech_ratio": 0.0,
            }

        n_frames = int(total_duration * 1000 / resolution_ms) + 1

        def segments_to_activity(segs: List[dict]) -> List[bool]:
            frames = [False] * n_frames
            for seg in segs:
                start_frame = int(float(seg.get("start", 0.0)) * 1000 / resolution_ms)
                end_frame = int(float(seg.get("end", 0.0)) * 1000 / resolution_ms)
                for frame_idx in range(max(0, start_frame), min(n_frames, end_frame)):
                    frames[frame_idx] = True
            return frames

        ref_frames = segments_to_activity(reference_segments)
        hyp_frames = segments_to_activity(hypothesis_segments)

        tp = fp = fn = tn = 0
        for ref_active, hyp_active in zip(ref_frames, hyp_frames):
            if ref_active and hyp_active:
                tp += 1
            elif not ref_active and hyp_active:
                fp += 1
            elif ref_active and not hyp_active:
                fn += 1
            else:
                tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / n_frames if n_frames > 0 else 0.0
        false_alarm_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        miss_rate = fn / (fn + tp) if (fn + tp) > 0 else 0.0

        return {
            "resolution_ms": float(resolution_ms),
            "tp": float(tp),
            "fp": float(fp),
            "fn": float(fn),
            "tn": float(tn),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "accuracy": round(accuracy, 4),
            "false_alarm_rate": round(false_alarm_rate, 4),
            "miss_rate": round(miss_rate, 4),
            "reference_speech_ratio": round(sum(ref_frames) / n_frames, 4),
            "hypothesis_speech_ratio": round(sum(hyp_frames) / n_frames, 4),
        }

    @staticmethod
    def calculate_der(
        hypothesis_segments: List[dict],
        reference_segments: List[dict],
        total_duration: float,
    ) -> float:
        """
        Basit DER (Diarization Error Rate) hesaplar.

        DER = (FA + Miss + Confusion) / Total_Reference_Duration

        Bu basitleştirilmiş bir hesaplamadır. Tam DER için pyannote.metrics
        kullanılması önerilir.

        Args:
            hypothesis_segments : Sistem çıktısı segmentler.
            reference_segments  : Referans (ground truth) segmentler.
            total_duration      : Toplam ses süresi (saniye).

        Returns:
            DER skoru [0.0, 1.0+].
        """
        if total_duration <= 0:
            return 0.0

        # Basit frame-bazlı karşılaştırma (100ms çözünürlük)
        resolution_ms = 100
        n_frames = int(total_duration * 1000 / resolution_ms) + 1

        def segments_to_frame_labels(
            segs: List[dict],
        ) -> List[set]:
            """Segmentleri frame-bazlı konuşmacı kümelerine dönüştürür."""
            frames: List[set] = [set() for _ in range(n_frames)]
            for seg in segs:
                start_frame = int(float(seg.get("start", 0)) * 1000 / resolution_ms)
                end_frame = int(float(seg.get("end", 0)) * 1000 / resolution_ms)

                speakers = seg.get("speakers", [])
                if not speakers:
                    speaker = seg.get("speaker", "")
                    if speaker and speaker != "overlap":
                        speakers = [speaker]

                for f in range(max(0, start_frame), min(n_frames, end_frame)):
                    frames[f].update(speakers)

            return frames

        ref_frames = segments_to_frame_labels(reference_segments)
        hyp_frames = segments_to_frame_labels(hypothesis_segments)

        total_errors = 0
        total_ref = 0

        for ref_set, hyp_set in zip(ref_frames, hyp_frames):
            n_ref = len(ref_set)
            total_ref += n_ref

            if n_ref == 0 and len(hyp_set) > 0:
                total_errors += len(hyp_set)  # False alarm
            elif n_ref > 0 and len(hyp_set) == 0:
                total_errors += n_ref  # Miss
            else:
                # Confusion: eşleşmeyen konuşmacılar
                matched = len(ref_set & hyp_set)
                total_errors += max(n_ref, len(hyp_set)) - matched

        return total_errors / max(total_ref, 1)

"""
rttm_writer.py
--------------
RTTM (Rich Transcription Time Marks) formatında okuma/yazma sınıfı.

Standart RTTM satır formatı:
    SPEAKER <file> <chn> <tbeg> <tdur> <ortho> <stype> <name> <conf> <slat>

Bu modül:
    - Segment listesini RTTM dosyasına yazar.
    - v2: Overlap segmentlerinde "overlap" etiketi yerine her konuşmacıyı
      ayrı bir RTTM satırı olarak yazar.
    - pyannote.audio uyumlu RTTM dosyaları üretir/okur.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from . import config

logger = logging.getLogger(config.LOGGER_NAME)

# RTTM alan sabitleri
_RTTM_TYPE = "SPEAKER"
_RTTM_CHANNEL = "1"
_RTTM_NA = "<NA>"


class RTTMParseError(Exception):
    """RTTM dosyası ayrıştırma hatası."""
    pass


class RTTMWriter:
    """
    Segment listesini standart RTTM formatında yazan ve okuyan sınıf.

    RTTM formatı, konuşmacı diyarizasyon sistemlerinde standart çıktı
    biçimidir ve pyannote.audio gibi kütüphanelerle doğrudan uyumludur.

    v2: Overlap segmentlerinde artık "overlap" etiketi yazılmaz.
    Her konuşmacı kendi RTTM satırını alır.

    Kullanım::

        writer = RTTMWriter()
        writer.write(segments, "output.rttm", recording_id="toplanti_01")
        loaded = writer.read("output.rttm")
    """

    def __init__(
        self,
        recording_id: str = config.DEFAULT_RECORDING_ID,
    ) -> None:
        """
        RTTMWriter örneği oluşturur.

        Args:
            recording_id : Varsayılan kayıt kimliği (write() çağrısında override edilebilir).
        """
        self.default_recording_id = recording_id

    # ------------------------------------------------------------------
    # Yazma
    # ------------------------------------------------------------------

    def write(
        self,
        segments: List[dict],
        output_path: str | Path,
        recording_id: Optional[str] = None,
    ) -> Path:
        """
        Segment listesini RTTM dosyasına yazar.

        # v2: Overlap segmentlerinde "overlap" etiketi yazılmaz.
        # Her konuşmacı ayrı bir RTTM satırı olarak yazılır:
        #   SPEAKER <id> 1 <start> <dur> <NA> <NA> speaker_0 <NA> <NA>
        #   SPEAKER <id> 1 <start> <dur> <NA> <NA> speaker_1 <NA> <NA>
        # type="single" olan segmentlerde davranış değişmedi.

        Args:
            segments     : MultiChannelVAD.process() çıktısı – List[dict].
            output_path  : RTTM dosyasının hedef yolu.
            recording_id : Kayıt kimliği (None ise varsayılan kullanılır).

        Returns:
            Yazılan dosyanın Path nesnesi.

        Raises:
            OSError   : Dosya yazma başarısızsa.
            ValueError: Segment listesi boşsa.
        """
        if not segments:
            raise ValueError("Yazılacak segment listesi boş olamaz.")

        rec_id = recording_id or self.default_recording_id
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "RTTM yazılıyor: %d segment → %s (rec_id=%s)",
            len(segments),
            output_path,
            rec_id,
        )

        lines: List[str] = []
        for seg in segments:
            lines.extend(self._segment_to_rttm_lines(seg, rec_id))

        with output_path.open("w", encoding="utf-8") as fh:
            for line in lines:
                fh.write(line + "\n")

        logger.info("RTTM yazma tamamlandı: %d satır → %s", len(lines), output_path)
        return output_path

    def write_string(
        self,
        segments: List[dict],
        recording_id: Optional[str] = None,
    ) -> str:
        """
        Segment listesini RTTM formatlı dize olarak döndürür (dosyaya yazmaz).

        Args:
            segments     : MultiChannelVAD.process() çıktısı.
            recording_id : Kayıt kimliği.

        Returns:
            RTTM içeriği tek bir string olarak.
        """
        rec_id = recording_id or self.default_recording_id
        lines: List[str] = []
        for seg in segments:
            lines.extend(self._segment_to_rttm_lines(seg, rec_id))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Okuma
    # ------------------------------------------------------------------

    def read(self, rttm_path: str | Path) -> List[dict]:
        """
        RTTM dosyasını okur ve segment listesi olarak döndürür.

        pyannote.audio uyumlu RTTM dosyalarını ayrıştırır:
            SPEAKER <file> <chn> <tbeg> <tdur> <ortho> <stype> <name> <conf> <slat>

        Args:
            rttm_path : RTTM dosyasının yolu.

        Returns:
            List[dict]: Her eleman bir segment sözlüğü:
                {
                    "recording_id": str,
                    "speaker": str,
                    "start": float,
                    "end": float,
                    "duration": float,
                    "type": "single" | "overlap" (overlap için birleştirme gerekmez)
                }

        Raises:
            FileNotFoundError : Dosya bulunamazsa.
            RTTMParseError    : Dosya formatı bozuksa.
        """
        rttm_path = Path(rttm_path)
        if not rttm_path.exists():
            raise FileNotFoundError(f"RTTM dosyası bulunamadı: {rttm_path}")

        segments: List[dict] = []
        with rttm_path.open("r", encoding="utf-8") as fh:
            for lineno, raw_line in enumerate(fh, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                seg = self._parse_rttm_line(line, lineno)
                segments.append(seg)

        logger.info("RTTM okundu: %d çizgi → %s", len(segments), rttm_path)
        return segments

    def read_grouped(self, rttm_path: str | Path) -> Dict[str, List[dict]]:
        """
        RTTM dosyasını okur ve kayıt kimliğine göre gruplar.

        Args:
            rttm_path : RTTM dosyasının yolu.

        Returns:
            {"recording_id": [segment, segment, ...], ...}
        """
        flat = self.read(rttm_path)
        grouped: Dict[str, List[dict]] = {}
        for seg in flat:
            rec = seg["recording_id"]
            grouped.setdefault(rec, []).append(seg)
        return grouped

    # ------------------------------------------------------------------
    # Dahili metodlar
    # ------------------------------------------------------------------

    @staticmethod
    def _segment_to_rttm_lines(seg: dict, rec_id: str) -> List[str]:
        """
        Tek bir segment sözlüğünden bir veya daha fazla RTTM satırı üretir.

        # v2: Overlap segmentlerinde "overlap" etiketi artık yazılmaz.
        # Her konuşmacı kendi satırını alır.
        # type="single" olan segmentlerde davranış değişmedi.

        Args:
            seg    : Segment sözlüğü (MultiChannelVAD çıktısı).
            rec_id : Kayıt kimliği.

        Returns:
            RTTM satır listesi.
        """
        start = float(seg["start"])
        end = float(seg["end"])
        duration = end - start
        seg_type = seg.get("type", "single")

        if duration <= 0:
            logger.warning(
                "Sıfır veya negatif süreli segment atlandı: %s [%.3f → %.3f]",
                seg.get("speaker"),
                start,
                end,
            )
            return []

        lines: List[str] = []

        if seg_type == "overlap":
            # v2: "overlap" etiketi yerine her konuşmacıyı ayrı satır olarak yaz
            speakers = seg.get("speakers", [])
            if not speakers:
                # Fallback: speakers listesi boşsa speaker alanını kullan
                # Ama "overlap" etiketini asla yazma — atla
                fallback_speaker = seg.get("speaker", "")
                if fallback_speaker and fallback_speaker != "overlap":
                    lines.append(
                        RTTMWriter._format_rttm_line(rec_id, start, duration, fallback_speaker)
                    )
            else:
                for spk in speakers:
                    # v2: "overlap" etiketinin kendisini asla yazma
                    if spk == "overlap":
                        continue
                    lines.append(
                        RTTMWriter._format_rttm_line(rec_id, start, duration, spk)
                    )
        else:
            speaker = seg.get("speaker", "unknown")
            lines.append(
                RTTMWriter._format_rttm_line(rec_id, start, duration, speaker)
            )

        return lines

    @staticmethod
    def _format_rttm_line(
        rec_id: str,
        start: float,
        duration: float,
        speaker: str,
    ) -> str:
        """
        Standart RTTM satırı oluşturur.

        Format:
            SPEAKER <file> 1 <tbeg> <tdur> <NA> <NA> <name> <NA> <NA>

        Args:
            rec_id   : Kayıt dosyası adı/kimliği.
            start    : Başlangıç zamanı (s).
            duration : Süre (s).
            speaker  : Konuşmacı etiketi.

        Returns:
            RTTM satırı (newline içermez).
        """
        return (
            f"{_RTTM_TYPE} {rec_id} {_RTTM_CHANNEL} "
            f"{start:.4f} {duration:.4f} "
            f"{_RTTM_NA} {_RTTM_NA} {speaker} {_RTTM_NA} {_RTTM_NA}"
        )

    @staticmethod
    def _parse_rttm_line(line: str, lineno: int) -> dict:
        """
        Tek bir RTTM satırını ayrıştırır.

        Args:
            line   : Ham satır metni.
            lineno : Hata mesajları için satır numarası.

        Returns:
            Segment sözlüğü.

        Raises:
            RTTMParseError : Beklenen alan sayısı yoksa veya tipler hatalıysa.
        """
        parts = line.split()
        if len(parts) < 10:
            raise RTTMParseError(
                f"Satır {lineno}: Beklenen ≥10 alan, bulundu {len(parts)}: '{line}'"
            )
        if parts[0] != "SPEAKER":
            raise RTTMParseError(
                f"Satır {lineno}: İlk alan 'SPEAKER' olmalı, bulundu '{parts[0]}'"
            )

        try:
            rec_id = parts[1]
            tbeg = float(parts[3])
            tdur = float(parts[4])
            speaker = parts[7]
        except (ValueError, IndexError) as exc:
            raise RTTMParseError(
                f"Satır {lineno}: Alan ayrıştırma hatası: {exc}"
            ) from exc

        return {
            "recording_id": rec_id,
            "speaker": speaker,
            "start": round(tbeg, 4),
            "end": round(tbeg + tdur, 4),
            "duration": round(tdur, 4),
            "type": "single",   # okunurken tek konuşmacı → single
        }

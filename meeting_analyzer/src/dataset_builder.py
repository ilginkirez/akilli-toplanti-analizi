"""
dataset_builder.py
------------------
Session kapandığında ayrı kaydedilen medya dosyalarını ve event loglarını
birleştirerek standart bir dataset klasörü oluşturur.

Çıktı yapısı:
    datasets/{session_id}/
        ├── audio/
        │   ├── {participant_id}.wav
        │   └── ...
        ├── metadata/
        │   ├── manifest.json
        │   ├── events.json
        │   └── speakers.rttm
        └── README.md

manifest.json formatı:
    {
        "session_id": "...",
        "participants": [...],
        "stream_mapping": {
            "participant_id": {
                "connection_id": "...",
                "stream_id": "...",
                "audio_file": "audio/{participant_id}.wav",
                "duration_sec": 123.4
            }
        },
        "recording_mode": "INDIVIDUAL",
        "total_duration_sec": 300.0
    }
"""

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("meeting_analyzer.dataset_builder")


class DatasetBuilder:
    """
    Session sonunda toplanan verileri standart dataset formatına dönüştürür.

    Akademik katkı: Post-hoc speaker identity recovery yerine,
    her kullanıcının ayrı stream olarak kesin eşleştirilmiş kaydını
    doğrudan dataset olarak sunar.
    """

    def __init__(self, output_dir: Optional[str] = None) -> None:
        self.output_dir = Path(output_dir or "./datasets")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("DatasetBuilder başlatıldı: output_dir=%s", self.output_dir)

    def build(
        self,
        session_id: str,
        participants: List[str],
        stream_mapping: Dict[str, Dict[str, Any]],
        audio_files: Dict[str, str],
        events_path: Optional[str] = None,
        speaking_segments: Optional[List[Dict[str, Any]]] = None,
        session_duration_sec: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Dataset klasörünü oluşturur.

        Args:
            session_id        : Oturum kimliği.
            participants      : Katılımcı kimlikleri.
            stream_mapping    : {participant_id: {connection_id, stream_id, ...}}
            audio_files       : {participant_id: wav_file_path}
            events_path       : Event JSON dosya yolu.
            speaking_segments : Konuşma segmentleri listesi.
            session_duration_sec : Toplam oturum süresi.

        Returns:
            Dataset bilgisi sözlüğü.
        """
        dataset_dir = self.output_dir / session_id
        audio_dir = dataset_dir / "audio"
        metadata_dir = dataset_dir / "metadata"

        audio_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "[session_id=%s] Dataset oluşturuluyor: %s",
            session_id,
            dataset_dir,
        )

        # 1. Ses dosyalarını kopyala
        copied_audio: Dict[str, str] = {}
        for participant_id, src_path in audio_files.items():
            src = Path(src_path)
            if src.exists():
                dest = audio_dir / f"{participant_id}.wav"
                shutil.copy2(str(src), str(dest))
                copied_audio[participant_id] = f"audio/{participant_id}.wav"
                logger.debug(
                    "Ses dosyası kopyalandı: %s -> %s", src, dest
                )
            else:
                logger.warning(
                    "Ses dosyası bulunamadı: %s", src_path
                )

        # 2. Manifest oluştur
        manifest = {
            "session_id": session_id,
            "created_at": time.strftime(
                "%Y-%m-%dT%H:%M:%S%z", time.localtime()
            ),
            "participants": participants,
            "participant_count": len(participants),
            "recording_mode": "INDIVIDUAL",
            "total_duration_sec": round(session_duration_sec, 2),
            "stream_mapping": {},
        }

        for pid in participants:
            sm = stream_mapping.get(pid, {})
            manifest["stream_mapping"][pid] = {
                "connection_id": sm.get("connection_id", ""),
                "stream_id": sm.get("stream_id", ""),
                "audio_file": copied_audio.get(pid, ""),
                "participant_id": pid,
            }

        manifest_path = metadata_dir / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)

        # 3. Events kopyala
        if events_path and Path(events_path).exists():
            shutil.copy2(events_path, str(metadata_dir / "events.json"))

        # 4. RTTM üret (konuşma segmentlerinden)
        rttm_path = metadata_dir / "speakers.rttm"
        self._write_rttm(rttm_path, session_id, speaking_segments or [])

        # 5. README oluştur
        readme_path = dataset_dir / "README.md"
        self._write_readme(
            readme_path, session_id, participants, session_duration_sec
        )

        result = {
            "session_id": session_id,
            "dataset_dir": str(dataset_dir),
            "manifest_path": str(manifest_path),
            "audio_files": copied_audio,
            "rttm_path": str(rttm_path),
            "participant_count": len(participants),
        }

        logger.info(
            "[session_id=%s] Dataset oluşturuldu: %s (%d katılımcı)",
            session_id,
            dataset_dir,
            len(participants),
        )

        return result

    @staticmethod
    def _write_rttm(
        output_path: Path,
        session_id: str,
        segments: List[Dict[str, Any]],
    ) -> None:
        """Konuşma segmentlerinden RTTM dosyası üretir."""
        with output_path.open("w", encoding="utf-8") as fh:
            for seg in segments:
                speaker = seg.get("participant_id", seg.get("speaker", "unknown"))
                start = float(seg.get("start", 0))
                duration = float(seg.get("end", 0)) - start
                if duration <= 0:
                    continue
                line = (
                    f"SPEAKER {session_id} 1 {start:.3f} {duration:.3f} "
                    f"<NA> <NA> {speaker} <NA> <NA>\n"
                )
                fh.write(line)

    @staticmethod
    def _write_readme(
        output_path: Path,
        session_id: str,
        participants: List[str],
        duration_sec: float,
    ) -> None:
        """Dataset için açıklayıcı README dosyası üretir."""
        content = f"""# Meeting Dataset: {session_id}

## Overview
- **Session ID**: {session_id}
- **Participants**: {len(participants)}
- **Duration**: {duration_sec:.1f} seconds
- **Recording Mode**: INDIVIDUAL (per-participant isolated streams)

## Participants
{chr(10).join(f"- {p}" for p in participants)}

## Structure
```
{session_id}/
├── audio/            # Per-participant WAV files
├── metadata/
│   ├── manifest.json # Stream→participant mapping
│   ├── events.json   # All session events with timestamps
│   └── speakers.rttm # Speaker-attributed speech segments
└── README.md
```

## Speaker Attribution
Each audio file corresponds to exactly one participant's
microphone input. Speaker identity is guaranteed by the
system architecture (individual stream recording), not by
post-hoc diarization algorithms.
"""
        with output_path.open("w", encoding="utf-8") as fh:
            fh.write(content)

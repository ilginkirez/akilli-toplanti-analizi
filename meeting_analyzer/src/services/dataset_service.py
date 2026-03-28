import subprocess
import json
import csv
from pathlib import Path
from datetime import datetime

class DatasetBuilder:
    def __init__(self, storage_path: str = "src/storage"):
        self.storage = Path(storage_path)

    def _load_session(self, session_id: str) -> dict:
        session_file = self.storage / "sessions" / session_id / "session.json"
        if not session_file.exists():
            return {"participants": []}
        return json.loads(session_file.read_text())

    def build(self, session_id: str) -> str:
        session = self._load_session(session_id)
        out = self.storage / "dataset" / session_id
        
        (out / "recordings" / "raw").mkdir(parents=True, exist_ok=True)
        (out / "recordings" / "wav").mkdir(parents=True, exist_ok=True)
        (out / "annotations").mkdir(parents=True, exist_ok=True)

        for p in session.get("participants", []):
            webm_name = p.get("recording_file")
            if not webm_name:
                continue
            webm = self.storage / "recordings" / webm_name
            wav = out / "recordings" / "wav" / f"{p['participant_id']}.wav"
            if webm.exists():
                self._convert_to_wav(webm, wav)
                p["wav_file"] = str(wav.relative_to(out))

        self._build_annotations(session, out)

        manifest = {
            "session_id": session_id,
            "built_at": datetime.utcnow().isoformat(),
            "participants": session.get("participants", []),
            "duration_sec": session.get("total_duration_sec"),
        }
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

        src = self.storage / "sessions" / session_id / "events.jsonl"
        if src.exists():
            (out / "events.jsonl").write_text(src.read_text())

        return str(out)

    def _convert_to_wav(self, src: Path, dst: Path):
        subprocess.run([
            "ffmpeg", "-y", "-i", str(src),
            "-ar", "16000", "-ac", "1",
            str(dst)
        ], capture_output=True)

    def _build_annotations(self, session: dict, out: Path):
        # Local import to prevent circular deps
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            from speech_tracker.vad import compute_segments
        except ImportError:
            return

        rows = []
        for p in session.get("participants", []):
            wav = out / "recordings" / "wav" / f"{p['participant_id']}.wav"
            if not wav.exists():
                continue
            segments = compute_segments(str(wav))
            for seg in segments:
                rows.append({
                    "participant_id": p.get("participant_id"),
                    "display_name": p.get("display_name"),
                    "begin_time": seg["start"],
                    "end_time": seg["end"],
                    "duration": seg["end"] - seg["start"],
                    "source": "vad_auto"
                })
        
        if rows:
            csv_path = out / "annotations" / "speaker_segments.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=rows[0].keys())
                w.writeheader()
                w.writerows(rows)

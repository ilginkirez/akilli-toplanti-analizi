import copy
import json
import os
import threading
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _from_timestamp_ms(timestamp_ms: Optional[int]) -> Optional[str]:
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()


def _jsonify(data: Any) -> Any:
    if not isinstance(data, str):
        return data

    text = data.strip()
    if not text:
        return {}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": data}


def _deep_merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


class SessionStore:
    def __init__(
        self,
        storage_root: str = "src/storage",
        recordings_dir: Optional[str] = None,
    ) -> None:
        self.storage_root = Path(storage_root)
        self.sessions_dir = self.storage_root / "sessions"
        self.recordings_dir = Path(
            recordings_dir or os.getenv("RECORDING_OUTPUT_DIR", "./recordings")
        )
        self._lock = threading.RLock()

        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: str) -> Path:
        return self.sessions_dir / session_id

    def _session_file(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "session.json"

    def _events_file(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "events.jsonl"

    def _default_session(self, session_id: str) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "created_at": _utc_now_iso(),
            "status": "active",
            "total_duration_sec": None,
            "participants": [],
            "connections": {},
            "streams": {},
            "recording": {
                "mode": "INDIVIDUAL",
                "name": session_id,
                "status": "pending",
                "recording_id": None,
                "has_audio": True,
                "has_video": False,
                "started_at": None,
                "stopped_at": None,
                "ready_at": None,
                "archive_path": None,
                "manifest_path": None,
                "size_bytes": None,
                "duration_sec": None,
                "reason": None,
                "files": [],
                "last_event": None,
            },
            "speech_analysis": {
                "status": "pending",
                "generated_at": None,
                "timebase": "recording",
                "recording_started_at": None,
                "segments_path": None,
                "rttm_path": None,
                "segments": [],
                "summary": [],
                "source_tracks": [],
                "error": None,
            },
            "webhook": {
                "events_received": 0,
                "last_event_at": None,
            },
        }

    def ensure_session(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            session_dir = self._session_dir(session_id)
            session_dir.mkdir(parents=True, exist_ok=True)
            self._events_file(session_id).touch(exist_ok=True)

            session_file = self._session_file(session_id)
            if session_file.exists():
                data = json.loads(session_file.read_text(encoding="utf-8"))
                merged = _deep_merge(self._default_session(session_id), data)
                session_file.write_text(
                    json.dumps(merged, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                return merged

            data = self._default_session(session_id)
            session_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return data

    def load_session(self, session_id: str) -> Dict[str, Any]:
        return self.ensure_session(session_id)

    def session_exists(self, session_id: str) -> bool:
        return self._session_file(session_id).exists()

    def save_session(self, session_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            session = _deep_merge(self._default_session(session_id), copy.deepcopy(data))
            self._session_dir(session_id).mkdir(parents=True, exist_ok=True)
            self._session_file(session_id).write_text(
                json.dumps(session, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            self._events_file(session_id).touch(exist_ok=True)
            return session

    def append_event(self, session_id: str, event: Dict[str, Any]) -> None:
        with self._lock:
            self.ensure_session(session_id)
            with self._events_file(session_id).open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def update_webhook_meta(self, session_id: str, timestamp_ms: Optional[int]) -> Dict[str, Any]:
        session = self.load_session(session_id)
        session["webhook"]["events_received"] += 1
        session["webhook"]["last_event_at"] = _from_timestamp_ms(timestamp_ms) or _utc_now_iso()
        return self.save_session(session_id, session)

    def _find_participant(self, session: Dict[str, Any], participant_id: str) -> Optional[Dict[str, Any]]:
        for participant in session["participants"]:
            if participant.get("participant_id") == participant_id:
                return participant
        return None

    def _find_participant_by_connection(
        self,
        session: Dict[str, Any],
        connection_id: str,
    ) -> Optional[Dict[str, Any]]:
        participant_id = session.get("connections", {}).get(connection_id)
        if participant_id:
            return self._find_participant(session, participant_id)

        for participant in session["participants"]:
            if participant.get("connection_id") == connection_id:
                return participant
        return None

    def register_pending_participant(
        self,
        session_id: str,
        participant_id: str,
        display_name: str,
        device_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        session = self.load_session(session_id)
        participant = self._find_participant(session, participant_id)
        if participant is None:
            participant = {
                "participant_id": participant_id,
                "display_name": display_name,
                "session_id": session_id,
                "connection_id": None,
                "stream_id": None,
                "stream_ids": [],
                "join_time": _utc_now_iso(),
                "leave_time": None,
                "active": True,
                "device_type": "unknown",
                "browser": "unknown",
                "os": "unknown",
                "audio_device": "unknown",
                "room_condition": "unknown",
                "network_type": "unknown",
                "network_notes": None,
                "client_data": {},
                "server_data": {},
                "location": None,
                "ip": None,
                "platform": None,
                "recording_file": None,
                "recording_files": [],
                "stream_recording_id": None,
            }
            session["participants"].append(participant)

        participant.update(
            {
                "display_name": display_name,
                "active": True,
                "leave_time": None,
            }
        )

        if device_info:
            participant["device_type"] = device_info.get("device_type", participant["device_type"])
            participant["browser"] = device_info.get("browser", participant["browser"])
            participant["os"] = device_info.get("os", participant["os"])
            participant["audio_device"] = device_info.get("audio_device", participant["audio_device"])
            participant["room_condition"] = device_info.get("room_condition", participant["room_condition"])
            participant["network_type"] = device_info.get("network_type", participant["network_type"])
            participant["network_notes"] = device_info.get("network_notes", participant["network_notes"])

        return self.save_session(session_id, session)

    def attach_connection(
        self,
        session_id: str,
        participant_id: Optional[str],
        connection_id: str,
        client_data: Optional[Dict[str, Any]] = None,
        server_data: Optional[Dict[str, Any]] = None,
        location: Optional[str] = None,
        ip: Optional[str] = None,
        platform: Optional[str] = None,
        connected_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        session = self.load_session(session_id)
        if participant_id is None and server_data:
            participant_id = server_data.get("participant_id")

        if participant_id is None:
            participant = self._find_participant_by_connection(session, connection_id)
        else:
            participant = self._find_participant(session, participant_id)

        if participant is None:
            inferred_name = None
            if client_data:
                inferred_name = client_data.get("display_name")
            if inferred_name is None and server_data:
                inferred_name = server_data.get("display_name")
            participant_id = participant_id or f"unknown_{connection_id}"
            self.register_pending_participant(
                session_id=session_id,
                participant_id=participant_id,
                display_name=inferred_name or participant_id,
            )
            session = self.load_session(session_id)
            participant = self._find_participant(session, participant_id)

        participant["connection_id"] = connection_id
        participant["client_data"] = client_data or participant.get("client_data", {})
        participant["server_data"] = server_data or participant.get("server_data", {})
        participant["location"] = location or participant.get("location")
        participant["ip"] = ip or participant.get("ip")
        participant["platform"] = platform or participant.get("platform")
        participant["active"] = True
        participant["leave_time"] = None
        if connected_at:
            participant["join_time"] = connected_at
        if server_data and server_data.get("display_name") and participant.get("display_name") in (None, "", "Unknown"):
            participant["display_name"] = server_data["display_name"]
        session["connections"][connection_id] = participant["participant_id"]
        return self.save_session(session_id, session)

    def attach_stream(
        self,
        session_id: str,
        connection_id: str,
        stream_id: str,
        audio_enabled: Optional[bool] = None,
        video_enabled: Optional[bool] = None,
        video_source: Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        session = self.load_session(session_id)
        participant = self._find_participant_by_connection(session, connection_id)
        participant_id = participant["participant_id"] if participant else None

        session["streams"][stream_id] = {
            "stream_id": stream_id,
            "connection_id": connection_id,
            "participant_id": participant_id,
            "audio_enabled": audio_enabled,
            "video_enabled": video_enabled,
            "video_source": video_source,
            "media_type": media_type or "audio_video",
            "recording_file": session.get("streams", {}).get(stream_id, {}).get("recording_file"),
        }

        if participant is not None:
            if stream_id not in participant["stream_ids"]:
                participant["stream_ids"].append(stream_id)
            participant["stream_id"] = stream_id

        return self.save_session(session_id, session)

    def mark_participant_left(
        self,
        session_id: str,
        participant_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        left_at: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        session = self.load_session(session_id)
        participant = None
        if participant_id:
            participant = self._find_participant(session, participant_id)
        elif connection_id:
            participant = self._find_participant_by_connection(session, connection_id)

        if participant is not None:
            participant["active"] = False
            participant["leave_time"] = left_at or _utc_now_iso()
            if reason:
                participant["leave_reason"] = reason

        if not any(item.get("active") for item in session["participants"]):
            session["status"] = "ended"

        return self.save_session(session_id, session)

    def can_start_recording(self, session_id: str) -> bool:
        session = self.load_session(session_id)
        status = session["recording"].get("status")
        if status in {"starting", "started", "stopped", "ready"}:
            return False
        session["recording"]["status"] = "starting"
        self.save_session(session_id, session)
        return True

    def update_recording(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        session = self.load_session(session_id)
        _deep_merge(session["recording"], updates)
        if session["recording"].get("status") == "started":
            session["status"] = "recording"
        return self.save_session(session_id, session)

    def update_speech_analysis(
        self,
        session_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        session = self.load_session(session_id)
        _deep_merge(session["speech_analysis"], updates)
        return self.save_session(session_id, session)

    def sync_individual_recording_archive(
        self,
        session_id: str,
        recording_name: Optional[str],
        recording_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        session = self.load_session(session_id)
        candidates = []
        for key in filter(None, [recording_name, recording_id, session_id]):
            candidates.extend(self.recordings_dir.glob(f"{key}*.zip"))
            candidates.extend(self.recordings_dir.rglob(f"{key}*.zip"))

        # Keep discovery stable when the same file is found by both glob and rglob.
        candidates = list(dict.fromkeys(candidates))

        if not candidates:
            return None

        archive_path = max(candidates, key=lambda item: item.stat().st_mtime)
        extract_dir = self.recordings_dir / session_id / "individual"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path) as bundle:
            manifest_name = next(
                (name for name in bundle.namelist() if name.lower().endswith(".json")),
                None,
            )
            if manifest_name is None:
                return None

            manifest = json.loads(bundle.read(manifest_name).decode("utf-8"))

            for member in bundle.namelist():
                if member.endswith("/"):
                    continue
                target = extract_dir / Path(member).name
                if target.exists():
                    continue
                with bundle.open(member) as src, target.open("wb") as dst:
                    dst.write(src.read())

        files = []
        for entry in manifest.get("files", []):
            server_data = _jsonify(entry.get("serverData"))
            client_data = _jsonify(entry.get("clientData"))
            stream_id = entry.get("streamId")
            connection_id = entry.get("connectionId")
            file_path = extract_dir / f"{stream_id}.webm"
            if not file_path.exists():
                matches = sorted(extract_dir.glob(f"{stream_id}*.webm"))
                file_path = matches[0] if matches else file_path

            participant_id = None
            if isinstance(server_data, dict):
                participant_id = server_data.get("participant_id")
            if participant_id is None:
                participant_id = session.get("connections", {}).get(connection_id)
            if participant_id is None:
                participant_id = session.get("streams", {}).get(stream_id, {}).get("participant_id")

            relative_path = None
            if file_path.exists():
                relative_path = file_path.relative_to(self.recordings_dir).as_posix()

            stream_state = session["streams"].setdefault(
                stream_id,
                {
                    "stream_id": stream_id,
                    "connection_id": connection_id,
                    "participant_id": participant_id,
                },
            )
            stream_state.update(
                {
                    "recording_file": relative_path,
                    "recording_size": entry.get("size"),
                    "audio_enabled": entry.get("hasAudio"),
                    "video_enabled": entry.get("hasVideo"),
                    "video_source": entry.get("typeOfVideo"),
                    "start_time_offset_ms": entry.get("startTimeOffset"),
                    "end_time_offset_ms": entry.get("endTimeOffset"),
                    "client_data": client_data,
                    "server_data": server_data,
                }
            )

            participant = self._find_participant(session, participant_id) if participant_id else None
            if participant is not None:
                recording_info = {
                    "stream_id": stream_id,
                    "connection_id": connection_id,
                    "file_path": relative_path,
                    "has_audio": entry.get("hasAudio"),
                    "has_video": entry.get("hasVideo"),
                    "type_of_video": entry.get("typeOfVideo"),
                    "start_time_offset_ms": entry.get("startTimeOffset"),
                    "end_time_offset_ms": entry.get("endTimeOffset"),
                    "size": entry.get("size"),
                }
                existing = participant.setdefault("recording_files", [])
                if recording_info not in existing:
                    existing.append(recording_info)
                if entry.get("hasAudio") and relative_path:
                    participant["recording_file"] = relative_path
                    participant["stream_recording_id"] = stream_id

            files.append(
                {
                    "participant_id": participant_id,
                    "connection_id": connection_id,
                    "stream_id": stream_id,
                    "file_path": relative_path,
                    "size": entry.get("size"),
                    "has_audio": entry.get("hasAudio"),
                    "has_video": entry.get("hasVideo"),
                    "client_data": client_data,
                    "server_data": server_data,
                }
            )

        session["recording"].update(
            {
                "archive_path": archive_path.relative_to(self.recordings_dir).as_posix(),
                "manifest_path": (extract_dir / Path(manifest_name).name).relative_to(self.recordings_dir).as_posix(),
                "files": files,
            }
        )

        manifest_target = extract_dir / Path(manifest_name).name
        manifest_target.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return self.save_session(session_id, session)


session_store = SessionStore()

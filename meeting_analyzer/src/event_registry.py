"""
event_registry.py
-----------------
Oturum olaylarını kaydeden ve sorgulayan modül.

Her olay aşağıdaki bağlamla kaydedilir:
    session_id -> participant_id -> connection_id -> stream_id -> timestamp

Olay türleri:
    - participantJoined / participantLeft
    - streamCreated / streamDestroyed
    - speakingStarted / speakingStopped
    - recordingStarted / recordingStopped
    - sessionCreated / sessionDestroyed
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("meeting_analyzer.event_registry")


class EventRegistry:
    """
    Oturum olaylarını zaman damgalı olarak kaydeder.

    participant_id -> connection_id -> stream_id zincirini
    her olay için koruyarak tam izlenebilirlik sağlar.
    """

    def __init__(self, output_dir: Optional[str] = None) -> None:
        self.output_dir = Path(output_dir or "./recordings")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # {session_id: [event_dict, ...]}
        self._events: Dict[str, List[Dict[str, Any]]] = {}

        # {session_id: {connection_id: participant_id}}
        self._identity_map: Dict[str, Dict[str, str]] = {}

        # {session_id: {stream_id: {connection_id, participant_id, ...}}}
        self._stream_map: Dict[str, Dict[str, Dict[str, Any]]] = {}

        logger.info("EventRegistry başlatıldı: output_dir=%s", self.output_dir)

    # ------------------------------------------------------------------
    # Olay Kayıt API'si
    # ------------------------------------------------------------------

    def log_event(
        self,
        session_id: str,
        event_type: str,
        participant_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        stream_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Yeni bir olay kaydeder.

        Args:
            session_id     : Oturum kimliği.
            event_type     : Olay türü.
            participant_id : Katılımcı kimliği.
            connection_id  : Bağlantı kimliği.
            stream_id      : Akış kimliği.
            metadata       : Ek meta veriler.

        Returns:
            Kaydedilen olay sözlüğü.
        """
        event = {
            "timestamp": time.time(),
            "timestamp_iso": time.strftime(
                "%Y-%m-%dT%H:%M:%S%z", time.localtime()
            ),
            "session_id": session_id,
            "event_type": event_type,
            "participant_id": participant_id,
            "connection_id": connection_id,
            "stream_id": stream_id,
            "metadata": metadata or {},
        }

        self._events.setdefault(session_id, []).append(event)

        logger.debug(
            "[session_id=%s] Olay kaydedildi: type=%s, participant=%s, "
            "stream=%s",
            session_id,
            event_type,
            participant_id,
            stream_id,
        )

        return event

    # ------------------------------------------------------------------
    # Kimlik Eşleştirme
    # ------------------------------------------------------------------

    def register_participant(
        self,
        session_id: str,
        participant_id: str,
        connection_id: str,
    ) -> None:
        """
        Katılımcı → bağlantı eşleşmesini kaydeder.
        """
        self._identity_map.setdefault(session_id, {})[connection_id] = participant_id

        self.log_event(
            session_id=session_id,
            event_type="participantJoined",
            participant_id=participant_id,
            connection_id=connection_id,
        )

        logger.info(
            "[session_id=%s] Katılımcı kaydedildi: %s -> %s",
            session_id,
            participant_id,
            connection_id,
        )

    def register_stream(
        self,
        session_id: str,
        stream_id: str,
        connection_id: str,
        media_type: str = "audio",
    ) -> None:
        """
        Akış → bağlantı → katılımcı zincirini kaydeder.
        """
        participant_id = self._identity_map.get(session_id, {}).get(
            connection_id, "unknown"
        )

        stream_info = {
            "stream_id": stream_id,
            "connection_id": connection_id,
            "participant_id": participant_id,
            "media_type": media_type,
            "created_at": time.time(),
        }

        self._stream_map.setdefault(session_id, {})[stream_id] = stream_info

        self.log_event(
            session_id=session_id,
            event_type="streamCreated",
            participant_id=participant_id,
            connection_id=connection_id,
            stream_id=stream_id,
            metadata={"media_type": media_type},
        )

        logger.info(
            "[session_id=%s] Stream kaydedildi: stream=%s -> "
            "participant=%s",
            session_id,
            stream_id,
            participant_id,
        )

    def log_speaking_event(
        self,
        session_id: str,
        participant_id: str,
        is_speaking: bool,
        connection_id: Optional[str] = None,
        stream_id: Optional[str] = None,
    ) -> None:
        """Konuşma başlangıç/bitiş olayını kaydeder."""
        event_type = "speakingStarted" if is_speaking else "speakingStopped"
        self.log_event(
            session_id=session_id,
            event_type=event_type,
            participant_id=participant_id,
            connection_id=connection_id,
            stream_id=stream_id,
        )

    # ------------------------------------------------------------------
    # Sorgulama
    # ------------------------------------------------------------------

    def get_events(
        self,
        session_id: str,
        event_type: Optional[str] = None,
        participant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Olay listesini filtreli döndürür."""
        events = self._events.get(session_id, [])

        if event_type:
            events = [e for e in events if e["event_type"] == event_type]
        if participant_id:
            events = [e for e in events if e["participant_id"] == participant_id]

        return events

    def get_identity_map(self, session_id: str) -> Dict[str, str]:
        """connection_id -> participant_id eşleşmesini döndürür."""
        return self._identity_map.get(session_id, {})

    def get_stream_map(self, session_id: str) -> Dict[str, Dict[str, Any]]:
        """stream_id -> {connection_id, participant_id, ...} döndürür."""
        return self._stream_map.get(session_id, {})

    def get_participant_for_stream(
        self, session_id: str, stream_id: str
    ) -> Optional[str]:
        """Stream ID'den katılımcı kimliğini çözümler."""
        stream_info = self._stream_map.get(session_id, {}).get(stream_id)
        return stream_info["participant_id"] if stream_info else None

    # ------------------------------------------------------------------
    # Dışa Aktarma
    # ------------------------------------------------------------------

    def export_session_events(self, session_id: str) -> str:
        """
        Oturum olaylarını JSON dosyasına yazar.

        Returns:
            JSON dosya yolu.
        """
        events = self._events.get(session_id, [])
        identity_map = self._identity_map.get(session_id, {})
        stream_map = self._stream_map.get(session_id, {})

        export_data = {
            "session_id": session_id,
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
            "identity_map": identity_map,
            "stream_map": stream_map,
            "events": events,
            "total_events": len(events),
        }

        output_path = self.output_dir / session_id / f"{session_id}_events.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(export_data, fh, indent=2, ensure_ascii=False, default=str)

        logger.info(
            "[session_id=%s] Olaylar dışa aktarıldı: %s (%d olay)",
            session_id,
            output_path,
            len(events),
        )

        return str(output_path)
"""
event_registry.py sonu
"""

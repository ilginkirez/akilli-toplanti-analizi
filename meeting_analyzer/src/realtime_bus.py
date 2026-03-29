"""
realtime_bus.py
---------------
Gerçek zamanlı VAD durumu yayın modülü.

FastAPI endpoint'leri:
    - WebSocket: ws://localhost:8000/ws/vad/{session_id}
    - SSE:       GET /api/vad/stream/{session_id}

Her 100ms'de bir VAD durumu broadcast edilir:
    {
        "timestamp_ms": 1234567890,
        "speakers": {
            "Alice": {"speaking": true, "energy": 0.043, "overlap": false},
            "Bob":   {"speaking": false, "energy": 0.002, "overlap": false}
        },
        "overlap_active": false
    }
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

logger = logging.getLogger("meeting_analyzer.realtime_bus")

# FastAPI Router
router = APIRouter()


class VADSessionManager:
    """
    Session bazlı WebSocket bağlantı yöneticisi.

    Her oturum için bağlı istemcileri takip eder ve VAD durumlarını
    tüm bağlı istemcilere broadcast eder.

    Attributes:
        sessions : {session_id: {websocket_set, vad_state, ...}} yapısı.
    """

    def __init__(self) -> None:
        """VADSessionManager örneği oluşturur."""
        # {session_id: {"clients": set, "vad_state": dict, "active": bool}}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._broadcast_tasks: Dict[str, asyncio.Task] = {}

        logger.info("VADSessionManager başlatıldı.")

    # ------------------------------------------------------------------
    # Session Yönetimi
    # ------------------------------------------------------------------

    def create_session(
        self,
        session_id: str,
        participants: List[str],
    ) -> None:
        """
        Yeni bir VAD yayın oturumu oluşturur.

        Args:
            session_id   : Oturum kimliği.
            participants : Katılımcı adları listesi.
        """
        if session_id in self._sessions:
            logger.warning(
                "[session_id=%s] Oturum zaten mevcut, sıfırlanıyor.",
                session_id,
            )

        # Başlangıç VAD durumu
        initial_speakers: Dict[str, Dict[str, Any]] = {}
        for name in participants:
            initial_speakers[name] = {
                "speaking": False,
                "energy": 0.0,
                "overlap": False,
            }

        self._sessions[session_id] = {
            "clients": set(),
            "sse_queues": [],
            "vad_state": {
                "timestamp_ms": 0,
                "speakers": initial_speakers,
                "overlap_active": False,
            },
            "participants": participants,
            "active": True,
        }

        logger.info(
            "[session_id=%s] VAD oturumu oluşturuldu: participants=%s",
            session_id,
            participants,
        )

    def close_session(self, session_id: str) -> None:
        """
        VAD yayın oturumunu kapatır.

        Args:
            session_id : Kapatılacak oturum kimliği.
        """
        session = self._sessions.get(session_id)
        if session:
            session["active"] = False
            # Broadcast görevini iptal et
            task = self._broadcast_tasks.pop(session_id, None)
            if task and not task.done():
                task.cancel()

            logger.info(
                "[session_id=%s] VAD oturumu kapatıldı. "
                "Bağlı istemci: %d",
                session_id,
                len(session["clients"]),
            )

    # ------------------------------------------------------------------
    # WebSocket Bağlantı Yönetimi
    # ------------------------------------------------------------------

    async def connect_client(
        self,
        session_id: str,
        websocket: WebSocket,
    ) -> bool:
        """
        WebSocket istemcisini oturuma bağlar.

        Args:
            session_id : Hedef oturum kimliği.
            websocket  : Bağlanacak WebSocket nesnesi.

        Returns:
            True: Bağlantı başarılı. False: Oturum bulunamadı.
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(
                "[session_id=%s] Oturum bulunamadı, bağlantı reddedildi.",
                session_id,
            )
            return False

        await websocket.accept()
        session["clients"].add(websocket)

        logger.info(
            "[session_id=%s] WebSocket istemcisi bağlandı. "
            "Toplam istemci: %d",
            session_id,
            len(session["clients"]),
        )
        return True

    def disconnect_client(
        self,
        session_id: str,
        websocket: WebSocket,
    ) -> None:
        """
        WebSocket istemcisini oturumdan ayırır.

        Args:
            session_id : Oturum kimliği.
            websocket  : Ayrılacak WebSocket nesnesi.
        """
        session = self._sessions.get(session_id)
        if session:
            session["clients"].discard(websocket)
            logger.info(
                "[session_id=%s] WebSocket istemcisi ayrıldı. "
                "Kalan istemci: %d",
                session_id,
                len(session["clients"]),
            )

    # ------------------------------------------------------------------
    # VAD Durumu Güncelleme & Broadcast
    # ------------------------------------------------------------------

    def update_vad_state(
        self,
        session_id: str,
        speakers: Dict[str, Dict[str, Any]],
        overlap_active: bool = False,
    ) -> None:
        """
        VAD durumunu günceller.

        Bu metod MultiChannelVAD frame sonuçlarından çağrılır.

        Args:
            session_id     : Oturum kimliği.
            speakers       : Konuşmacı durumları.
            overlap_active : Overlap var mı?
        """
        session = self._sessions.get(session_id)
        if not session:
            return

        session["vad_state"] = {
            "timestamp_ms": int(time.time() * 1000),
            "speakers": speakers,
            "overlap_active": overlap_active,
        }

    async def broadcast_vad_state(
        self,
        session_id: str,
    ) -> int:
        """
        Güncel VAD durumunu tüm bağlı WebSocket istemcilerine gönderir.

        Args:
            session_id : Oturum kimliği.

        Returns:
            Mesaj gönderilen istemci sayısı.
        """
        session = self._sessions.get(session_id)
        if not session:
            return 0

        vad_state = session["vad_state"]
        message = json.dumps(vad_state)

        disconnected: Set[WebSocket] = set()
        sent_count = 0

        for ws in session["clients"]:
            try:
                await ws.send_text(message)
                sent_count += 1
            except Exception:
                disconnected.add(ws)

        # Bağlantısı kopan istemcileri temizle
        for ws in disconnected:
            session["clients"].discard(ws)
            logger.debug(
                "[session_id=%s] Kopuk istemci temizlendi.",
                session_id,
            )

        # SSE kuyruklarına da gönder
        for queue in session.get("sse_queues", []):
            try:
                queue.put_nowait(vad_state)
            except asyncio.QueueFull:
                pass

        return sent_count

    async def start_broadcast_loop(
        self,
        session_id: str,
        interval_ms: int = 100,
    ) -> None:
        """
        Belirtilen aralıklarla VAD durumunu sürekli broadcast eder.

        Args:
            session_id  : Oturum kimliği.
            interval_ms : Broadcast aralığı (ms). Varsayılan: 100.
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(
                "[session_id=%s] Broadcast loop başlatılamadı: oturum yok.",
                session_id,
            )
            return

        interval_sec = interval_ms / 1000.0

        logger.info(
            "[session_id=%s] Broadcast loop başlatıldı: interval=%dms",
            session_id,
            interval_ms,
        )

        while session.get("active", False):
            await self.broadcast_vad_state(session_id)
            await asyncio.sleep(interval_sec)

        logger.info(
            "[session_id=%s] Broadcast loop sonlandı.",
            session_id,
        )

    def register_sse_queue(
        self,
        session_id: str,
        queue: asyncio.Queue,
    ) -> bool:
        """
        SSE istemcisi için bir kuyruk kaydeder.

        Args:
            session_id : Oturum kimliği.
            queue      : asyncio.Queue nesnesi.

        Returns:
            True: Başarılı. False: Oturum yok.
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        session.setdefault("sse_queues", []).append(queue)
        return True

    def unregister_sse_queue(
        self,
        session_id: str,
        queue: asyncio.Queue,
    ) -> None:
        """SSE kuyruğunu kaldırır."""
        session = self._sessions.get(session_id)
        if session and "sse_queues" in session:
            try:
                session["sse_queues"].remove(queue)
            except ValueError:
                pass


# ──────────────────────────────────────────────────────────────────────────────
# Global Session Manager (Router tarafından kullanılır)
# ──────────────────────────────────────────────────────────────────────────────

vad_session_manager = VADSessionManager()


# ──────────────────────────────────────────────────────────────────────────────
# RealtimeBus — Router + Yardımcı Sınıf
# ──────────────────────────────────────────────────────────────────────────────

class RealtimeBus:
    """
    Gerçek zamanlı VAD yayın sistemi.

    FastAPI router'ını ve VADSessionManager'ı bir arada yönetir.

    Attributes:
        manager : VADSessionManager örneği.
        router  : FastAPI APIRouter.
    """

    def __init__(
        self,
        manager: Optional[VADSessionManager] = None,
    ) -> None:
        """
        RealtimeBus örneği oluşturur.

        Args:
            manager : İsteğe bağlı VADSessionManager. None ise global kullanılır.
        """
        self.manager = manager or vad_session_manager
        self.router = router

        logger.info("RealtimeBus başlatıldı.")

    def get_router(self) -> APIRouter:
        """FastAPI router nesnesini döndürür."""
        return self.router


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI Endpoint'leri
# ──────────────────────────────────────────────────────────────────────────────

@router.websocket("/ws/vad/{session_id}")
async def websocket_vad_endpoint(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """
    WebSocket üzerinden gerçek zamanlı VAD durumu yayınlar.

    Her 100ms'de bir bağlı istemcilere VAD durumu gönderilir.
    İstemci bağlantısı koptuğunda otomatik temizlenir.

    Args:
        websocket  : FastAPI WebSocket nesnesi.
        session_id : Hedef oturum kimliği.
    """
    manager = vad_session_manager

    connected = await manager.connect_client(session_id, websocket)
    if not connected:
        await websocket.close(code=4004, reason="Session not found")
        return

    try:
        # İstemci mesajlarını dinle (ping/pong veya kontrol mesajları)
        while True:
            try:
                data = await websocket.receive_text()
                # İstemciden gelen mesaj — şimdilik sadece log
                logger.debug(
                    "[session_id=%s] WebSocket mesajı alındı: %s",
                    session_id,
                    data[:100],
                )
            except WebSocketDisconnect:
                break
    finally:
        manager.disconnect_client(session_id, websocket)


@router.get("/api/vad/stream/{session_id}")
async def sse_vad_endpoint(session_id: str) -> StreamingResponse:
    """
    Server-Sent Events (SSE) üzerinden gerçek zamanlı VAD durumu yayınlar.

    GET /api/vad/stream/{session_id}

    Args:
        session_id : Hedef oturum kimliği.

    Returns:
        StreamingResponse: text/event-stream MIME tipi ile SSE akışı.
    """
    manager = vad_session_manager

    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    registered = manager.register_sse_queue(session_id, queue)

    if not registered:
        async def error_stream():
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
        )

    async def event_stream():
        """SSE olay akışı üreteci."""
        try:
            while True:
                try:
                    vad_state = await asyncio.wait_for(
                        queue.get(), timeout=30.0
                    )
                    yield f"data: {json.dumps(vad_state)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive
                    yield f": keepalive\n\n"
        finally:
            manager.unregister_sse_queue(session_id, queue)

    logger.info(
        "[session_id=%s] SSE istemcisi bağlandı.",
        session_id,
    )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

"""
openvidu_connector.py
---------------------
OpenVidu Server REST API ile iletişim modülü.

OpenVidu 2.x uyumlu REST API'sini kullanarak:
- Oturum oluşturma/kapatma
- Katılımcı bağlantı token'ı üretme
- Oturum bilgisi sorgulama

Bağlantı bilgileri .env dosyasından okunur:
    OPENVIDU_URL=http://localhost:4443
    OPENVIDU_SECRET=MY_SECRET
"""

import logging
import os
import ssl
from typing import Any, Dict, List, Optional

import aiohttp
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

logger = logging.getLogger("meeting_analyzer.openvidu")


class OpenViduConnectionError(Exception):
    """OpenVidu sunucusu ile iletişim hatası."""
    pass


class OpenViduSessionError(Exception):
    """Oturum oluşturma/yönetme hatası."""
    pass


class OpenViduConnector:
    """
    OpenVidu Server REST API istemcisi.

    OpenVidu 2.x uyumlu REST API'sini kullanarak
    oturum yönetimi ve katılımcı bağlantısı sağlar.

    Attributes:
        base_url   (str)  : OpenVidu sunucu adresi.
        secret     (str)  : OpenVidu API anahtarı.
        verify_ssl (bool) : SSL doğrulaması (geliştirme: False).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        secret: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
    ) -> None:
        """
        OpenViduConnector örneği oluşturur.

        Args:
            base_url   : OpenVidu sunucu URL'si. None ise OPENVIDU_URL env değişkeninden okunur.
            secret     : API anahtarı. None ise OPENVIDU_SECRET env değişkeninden okunur.
            verify_ssl : SSL doğrulaması. None ise SSL_VERIFY env değişkeninden okunur.

        Raises:
            ValueError : URL veya secret eksikse.
        """
        resolved_base_url = os.getenv("OPENVIDU_URL", "") if base_url is None else base_url
        resolved_secret = os.getenv("OPENVIDU_SECRET", "") if secret is None else secret

        self.base_url = resolved_base_url.rstrip("/")
        self.secret = resolved_secret
        
        if verify_ssl is not None:
            self.verify_ssl = verify_ssl
        else:
            self.verify_ssl = os.getenv("SSL_VERIFY", "false").lower() == "true"

        if not self.base_url:
            raise ValueError(
                "OpenVidu URL belirtilmedi. OPENVIDU_URL env değişkenini "
                "veya base_url parametresini ayarlayın."
            )
        if not self.secret:
            raise ValueError(
                "OpenVidu secret belirtilmedi. OPENVIDU_SECRET env değişkenini "
                "veya secret parametresini ayarlayın."
            )

        self._session: Optional[aiohttp.ClientSession] = None

        logger.info(
            "OpenViduConnector başlatıldı: url=%s, verify_ssl=%s",
            self.base_url,
            self.verify_ssl,
        )

    # ------------------------------------------------------------------
    # HTTP Session Yönetimi
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Tembel (lazy) aiohttp.ClientSession oluşturur veya mevcut olanı döndürür.

        Returns:
            aiohttp.ClientSession: Yapılandırılmış HTTP istemci oturumu.
        """
        if self._session is None or self._session.closed:
            auth = aiohttp.BasicAuth("OPENVIDUAPP", self.secret)

            # SSL yapılandırması
            ssl_context: Any = None
            if not self.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = aiohttp.ClientSession(
                auth=auth,
                connector=connector,
                headers={"Content-Type": "application/json"},
            )

        return self._session

    async def close(self) -> None:
        """HTTP istemci oturumunu kapatır."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("HTTP istemci oturumu kapatıldı.")

    # ------------------------------------------------------------------
    # Oturum API'si
    # ------------------------------------------------------------------

    async def create_session(
        self,
        session_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Yeni bir OpenVidu oturumu oluşturur.

        Args:
            session_id : İsteğe bağlı özel oturum kimliği.
                         None ise OpenVidu otomatik üretir.
            properties : Ek oturum özellikleri (mediaMode, recordingMode vb.).

        Returns:
            OpenVidu API yanıtı (session bilgileri).

        Raises:
            OpenViduSessionError   : Oturum oluşturulamazsa.
            OpenViduConnectionError: Sunucuya bağlanılamazsa.
        """
        url = f"{self.base_url}/openvidu/api/sessions"
        payload: Dict[str, Any] = properties.copy() if properties else {}

        if session_id:
            payload["customSessionId"] = session_id

        logger.info(
            "[session_id=%s] Oturum oluşturuluyor...",
            session_id or "auto",
        )

        response_data = await self._request("POST", url, json_data=payload)

        actual_session_id = response_data.get("id", session_id)
        logger.info(
            "[session_id=%s] Oturum başarıyla oluşturuldu.",
            actual_session_id,
        )

        return response_data

    async def create_connection(
        self,
        session_id: str,
        participant_name: str,
        role: str = "PUBLISHER",
        data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Mevcut bir oturuma katılımcı bağlantısı oluşturur ve token döndürür.

        Args:
            session_id       : Hedef oturum kimliği.
            participant_name : Katılımcı adı (metadata olarak gönderilir).
            role             : Katılımcı rolü (PUBLISHER, SUBSCRIBER, MODERATOR).
            data             : İsteğe bağlı ek veri (JSON string).

        Returns:
            Bağlantı bilgileri (token dahil).

        Raises:
            OpenViduSessionError   : Bağlantı oluşturulamazsa.
            OpenViduConnectionError: Sunucuya bağlanılamazsa.
        """
        url = f"{self.base_url}/openvidu/api/sessions/{session_id}/connection"

        metadata = data or f'{{"clientData": "{participant_name}"}}'
        payload: Dict[str, Any] = {
            "role": role,
            "data": metadata,
        }

        logger.info(
            "[session_id=%s] Bağlantı oluşturuluyor: participant=%s, role=%s",
            session_id,
            participant_name,
            role,
        )

        response_data = await self._request("POST", url, json_data=payload)

        token = response_data.get("token", "")
        logger.info(
            "[session_id=%s] Token üretildi: participant=%s, token=%s...",
            session_id,
            participant_name,
            token[:30] if token else "N/A",
        )

        return response_data

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Oturum bilgilerini sorgular.

        Args:
            session_id : Sorgulanacak oturum kimliği.

        Returns:
            Oturum detayları (katılımcılar, bağlantılar vb.).

        Raises:
            OpenViduSessionError   : Oturum bulunamazsa.
            OpenViduConnectionError: Sunucuya bağlanılamazsa.
        """
        url = f"{self.base_url}/openvidu/api/sessions/{session_id}"

        logger.debug("[session_id=%s] Oturum bilgisi sorgulanıyor...", session_id)

        return await self._request("GET", url)

    async def close_session(self, session_id: str) -> bool:
        """
        Oturumu kapatır ve tüm bağlantıları sonlandırır.

        Args:
            session_id : Kapatılacak oturum kimliği.

        Returns:
            True: Oturum başarıyla kapatıldı.

        Raises:
            OpenViduSessionError   : Oturum kapatılamazsa.
            OpenViduConnectionError: Sunucuya bağlanılamazsa.
        """
        url = f"{self.base_url}/openvidu/api/sessions/{session_id}"

        logger.info("[session_id=%s] Oturum kapatılıyor...", session_id)

        session = await self._get_session()
        try:
            async with session.delete(url) as resp:
                if resp.status == 204:
                    logger.info(
                        "[session_id=%s] Oturum başarıyla kapatıldı.", session_id
                    )
                    return True
                elif resp.status == 404:
                    logger.warning(
                        "[session_id=%s] Oturum bulunamadı (zaten kapatılmış olabilir).",
                        session_id,
                    )
                    return True
                else:
                    text = await resp.text()
                    raise OpenViduSessionError(
                        f"[session_id={session_id}] Oturum kapatılamadı "
                        f"(HTTP {resp.status}): {text}"
                    )
        except aiohttp.ClientError as exc:
            raise OpenViduConnectionError(
                f"[session_id={session_id}] Sunucu bağlantı hatası: {exc}"
            ) from exc

    async def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Tüm aktif oturumları listeler.

        Returns:
            Aktif oturum listesi.
        """
        url = f"{self.base_url}/openvidu/api/sessions"
        logger.debug("Aktif oturumlar sorgulanıyor...")

        response_data = await self._request("GET", url)
        sessions = response_data.get("content", [])

        logger.debug("Aktif oturum sayısı: %d", len(sessions))
        return sessions

    # ------------------------------------------------------------------
    # Dahili HTTP İstek Yardımcısı
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        HTTP isteği gönderir ve JSON yanıtını döndürür.

        Args:
            method    : HTTP metodu (GET, POST, DELETE vb.).
            url       : Hedef URL.
            json_data : İstek gövdesi (POST için).

        Returns:
            JSON olarak ayrıştırılmış yanıt.

        Raises:
            OpenViduConnectionError: Bağlantı hatası.
            OpenViduSessionError   : HTTP hata kodu (4xx/5xx).
        """
        session = await self._get_session()

        try:
            async with session.request(method, url, json=json_data) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                elif resp.status == 204:
                    return {}
                elif resp.status == 404:
                    raise OpenViduSessionError(
                        f"Kaynak bulunamadı (404): {url}"
                    )
                elif resp.status == 409:
                    # Session zaten var — mevcut bilgileri döndür
                    logger.warning(
                        "Kaynak zaten mevcut (409): %s — mevcut bilgi döndürülüyor.",
                        url,
                    )
                    try:
                        return await resp.json()
                    except Exception:
                        return {"status": "conflict"}
                else:
                    text = await resp.text()
                    raise OpenViduSessionError(
                        f"OpenVidu API hatası (HTTP {resp.status}): {text}"
                    )
        except aiohttp.ClientError as exc:
            raise OpenViduConnectionError(
                f"OpenVidu sunucusuna bağlanılamadı: {url} → {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Context Manager Desteği
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "OpenViduConnector":
        """Async context manager giriş."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager çıkış — HTTP oturumunu kapatır."""
        await self.close()

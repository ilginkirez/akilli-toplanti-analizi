"""
video_recorder.py
-----------------
OpenVidu COMPOSED mod ile composite video kaydı modülü.

Tüm katılımcıları tek bir karede birleştirerek WebM/VP8 formatında kaydeder.
Zaman damgası ile RTTM çıktısı senkronize edilir (ortak base_timestamp).

Kayıt parametreleri:
    - outputMode: COMPOSED
    - resolution: 1280x720
    - frameRate: 30
    - Çıktı: {session_id}_composite_{timestamp}.webm
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("meeting_analyzer.video_recorder")


class VideoRecordingError(Exception):
    """Video kaydı sırasında oluşan hatalar için özel exception."""
    pass


class VideoRecorder:
    """
    OpenVidu COMPOSED mod video kayıt yöneticisi.

    Tüm katılımcıların video akışlarını tek bir karede birleştirerek
    composite video dosyası oluşturur.

    Attributes:
        connector  : OpenViduConnector örneği.
        output_dir : Video dosyalarının yazılacağı dizin.
        resolution : Video çözünürlüğü (genişlikxYükseklik).
        frame_rate : Video kare hızı (fps).
    """

    # Varsayılan video parametreleri
    DEFAULT_RESOLUTION: str = "1280x720"
    DEFAULT_FRAME_RATE: int = 30

    def __init__(
        self,
        connector: Any,
        output_dir: Optional[str] = None,
        resolution: str = DEFAULT_RESOLUTION,
        frame_rate: int = DEFAULT_FRAME_RATE,
    ) -> None:
        """
        VideoRecorder örneği oluşturur.

        Args:
            connector  : OpenViduConnector örneği (REST API iletişimi için).
            output_dir : Video dosyalarının yazılacağı dizin.
            resolution : Video çözünürlüğü. Varsayılan: "1280x720".
            frame_rate : Kare hızı (fps). Varsayılan: 30.
        """
        self.connector = connector
        self.output_dir = Path(
            output_dir or os.getenv("RECORDING_OUTPUT_DIR", "./recordings")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.resolution = resolution
        self.frame_rate = frame_rate

        # Aktif kayıtları takip: {recording_id: {...metadata...}}
        self.active_recordings: Dict[str, Dict[str, Any]] = {}

        logger.info(
            "VideoRecorder başlatıldı: output_dir=%s, resolution=%s, fps=%d",
            self.output_dir,
            self.resolution,
            self.frame_rate,
        )

    # ------------------------------------------------------------------
    # Kayıt API'si
    # ------------------------------------------------------------------

    async def start_recording(
        self,
        session_id: str,
        base_timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Oturum için composite video kaydı başlatır.

        OpenVidu Recording API: POST /openvidu/api/recordings/start
        outputMode: COMPOSED — tüm katılımcılar tek karede.

        Args:
            session_id     : Kayıt yapılacak oturum kimliği.
            base_timestamp : Senkronizasyon için temel zaman damgası.
                             None ise time.time() kullanılır.

        Returns:
            Kayıt bilgileri (recording_id, başlangıç zamanı vb.).

        Raises:
            VideoRecordingError: Kayıt başlatılamazsa.
        """
        start_timestamp = base_timestamp or time.time()

        url = f"{self.connector.base_url}/openvidu/api/recordings/start"
        payload: Dict[str, Any] = {
            "session": session_id,
            "outputMode": "COMPOSED",
            "hasAudio": True,
            "hasVideo": True,
            "resolution": self.resolution,
            "frameRate": self.frame_rate,
        }

        logger.info(
            "[session_id=%s] Video kaydı başlatılıyor (COMPOSED mod): "
            "resolution=%s, fps=%d",
            session_id,
            self.resolution,
            self.frame_rate,
        )

        try:
            response = await self.connector._request("POST", url, json_data=payload)
        except Exception as exc:
            raise VideoRecordingError(
                f"[session_id={session_id}] Video kaydı başlatılamadı: {exc}"
            ) from exc

        recording_id = response.get("id", "")
        timestamp_str = str(int(start_timestamp))

        # Beklenen çıktı dosya yolu
        video_filename = f"{session_id}_composite_{timestamp_str}.webm"
        video_path = str(self.output_dir / video_filename)

        recording_info: Dict[str, Any] = {
            "recording_id": recording_id,
            "session_id": session_id,
            "start_timestamp": start_timestamp,
            "start_timestamp_iso": time.strftime(
                "%Y-%m-%dT%H:%M:%S%z", time.localtime(start_timestamp)
            ),
            "base_timestamp": start_timestamp,
            "status": "started",
            "output_mode": "COMPOSED",
            "resolution": self.resolution,
            "frame_rate": self.frame_rate,
            "video_path": video_path,
            "api_response": response,
        }

        self.active_recordings[recording_id] = recording_info

        logger.info(
            "[session_id=%s] Video kaydı başlatıldı: recording_id=%s, "
            "video_path=%s, base_ts=%.3f",
            session_id,
            recording_id,
            video_path,
            start_timestamp,
        )

        return recording_info

    async def stop_recording(
        self,
        recording_id: str,
    ) -> Dict[str, Any]:
        """
        Aktif video kaydını durdurur.

        Args:
            recording_id : Durdurulacak kayıt kimliği.

        Returns:
            Kayıt sonuç bilgileri (dosya yolları, süre vb.).

        Raises:
            VideoRecordingError: Kayıt durdurulamazsa.
        """
        stop_timestamp = time.time()

        url = (
            f"{self.connector.base_url}/openvidu/api/recordings/stop/{recording_id}"
        )

        logger.info(
            "[recording_id=%s] Video kaydı durduruluyor...",
            recording_id,
        )

        try:
            response = await self.connector._request("POST", url)
        except Exception as exc:
            raise VideoRecordingError(
                f"[recording_id={recording_id}] Video kaydı durdurulamadı: {exc}"
            ) from exc

        recording_info = self.active_recordings.get(recording_id, {})
        recording_info.update({
            "stop_timestamp": stop_timestamp,
            "stop_timestamp_iso": time.strftime(
                "%Y-%m-%dT%H:%M:%S%z", time.localtime(stop_timestamp)
            ),
            "status": "stopped",
            "duration_sec": stop_timestamp - recording_info.get(
                "start_timestamp", stop_timestamp
            ),
            "api_response_stop": response,
        })

        logger.info(
            "[recording_id=%s] Video kaydı durduruldu: duration=%.1fs, "
            "video_path=%s",
            recording_id,
            recording_info.get("duration_sec", 0),
            recording_info.get("video_path", "N/A"),
        )

        return recording_info

    async def get_recording_info(
        self,
        recording_id: str,
    ) -> Dict[str, Any]:
        """
        Kayıt meta verisini OpenVidu API'sinden sorgular.

        Args:
            recording_id : Sorgulanacak kayıt kimliği.

        Returns:
            Kayıt meta verisi.
        """
        url = (
            f"{self.connector.base_url}/openvidu/api/recordings/{recording_id}"
        )

        logger.debug(
            "[recording_id=%s] Video kayıt bilgisi sorgulanıyor...",
            recording_id,
        )

        return await self.connector._request("GET", url)

    def get_video_path(
        self,
        session_id: str,
        timestamp: float,
    ) -> str:
        """
        Beklenen video dosya yolunu üretir.

        Args:
            session_id : Oturum kimliği.
            timestamp  : Kayıt başlangıç zaman damgası.

        Returns:
            Beklenen video dosya yolu.
        """
        timestamp_str = str(int(timestamp))
        filename = f"{session_id}_composite_{timestamp_str}.webm"
        return str(self.output_dir / filename)

    def get_sync_offset(
        self,
        recording_id: str,
    ) -> float:
        """
        Kayıt için base_timestamp'i döndürür (RTTM senkronizasyonu için).

        Args:
            recording_id : Kayıt kimliği.

        Returns:
            Base timestamp (Unix epoch).

        Raises:
            VideoRecordingError: Kayıt bulunamazsa.
        """
        info = self.active_recordings.get(recording_id)
        if info is None:
            raise VideoRecordingError(
                f"Kayıt bulunamadı: {recording_id}"
            )
        return float(info.get("base_timestamp", 0.0))

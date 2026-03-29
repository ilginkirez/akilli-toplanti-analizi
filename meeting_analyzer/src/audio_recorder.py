"""
audio_recorder.py
-----------------
OpenVidu individual stream recording ile katılımcı bazlı ses kaydı modülü.

Her katılımcının audio track'i ayrı bir dosyaya kaydedilir (WebM/Opus).
Kayıt bitince AudioStandardizer'a otomatik olarak beslenir.

Dosya adı formatı: {session_id}_{participant_name}_{timestamp}.webm
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("meeting_analyzer.audio_recorder")


class AudioRecordingError(Exception):
    """Ses kaydı sırasında oluşan hatalar için özel exception."""
    pass


class AudioRecorder:
    """
    OpenVidu individual stream recording yöneticisi.

    Her katılımcının ses akışını ayrı dosyalara kaydeder ve
    kayıt bittikten sonra AudioStandardizer pipeline'ına besler.

    Attributes:
        connector       : OpenViduConnector örneği.
        output_dir      : Kayıt dosyalarının yazılacağı dizin.
        active_recordings : Aktif kayıt bilgilerini tutan sözlük.
    """

    def __init__(
        self,
        connector: Any,
        output_dir: Optional[str] = None,
    ) -> None:
        """
        AudioRecorder örneği oluşturur.

        Args:
            connector  : OpenViduConnector örneği (REST API iletişimi için).
            output_dir : Kayıt dosyalarının yazılacağı dizin.
                         None ise RECORDING_OUTPUT_DIR env değişkeninden okunur.
        """
        self.connector = connector
        self.output_dir = Path(
            output_dir or os.getenv("RECORDING_OUTPUT_DIR", "./recordings")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Aktif kayıtları takip: {recording_id: {...metadata...}}
        self.active_recordings: Dict[str, Dict[str, Any]] = {}

        logger.info(
            "AudioRecorder başlatıldı: output_dir=%s",
            self.output_dir,
        )

    # ------------------------------------------------------------------
    # Kayıt API'si
    # ------------------------------------------------------------------

    async def start_recording(
        self,
        session_id: str,
        participants: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Oturum için individual stream recording başlatır.

        OpenVidu Recording API: POST /openvidu/api/recordings/start
        outputMode: INDIVIDUAL — her katılımcı ayrı dosyaya kaydedilir.

        Args:
            session_id   : Kayıt yapılacak oturum kimliği.
            participants : Katılımcı isim listesi (loglama amaçlı).

        Returns:
            Kayıt bilgileri (recording_id, başlangıç zamanı vb.).

        Raises:
            AudioRecordingError: Kayıt başlatılamazsa.
        """
        start_timestamp = time.time()

        url = f"{self.connector.base_url}/openvidu/api/recordings/start"
        payload: Dict[str, Any] = {
            "session": session_id,
            "outputMode": "INDIVIDUAL",
            "hasAudio": True,
            "hasVideo": False,
        }

        logger.info(
            "[session_id=%s] Ses kaydı başlatılıyor (INDIVIDUAL mod)... "
            "Katılımcılar: %s",
            session_id,
            participants or "bilinmiyor",
        )

        try:
            response = await self.connector._request("POST", url, json_data=payload)
        except Exception as exc:
            raise AudioRecordingError(
                f"[session_id={session_id}] Ses kaydı başlatılamadı: {exc}"
            ) from exc

        recording_id = response.get("id", "")

        # Kayıt meta verisi
        recording_info: Dict[str, Any] = {
            "recording_id": recording_id,
            "session_id": session_id,
            "participants": participants or [],
            "start_timestamp": start_timestamp,
            "start_timestamp_iso": time.strftime(
                "%Y-%m-%dT%H:%M:%S%z", time.localtime(start_timestamp)
            ),
            "status": "started",
            "output_mode": "INDIVIDUAL",
            "api_response": response,
        }

        self.active_recordings[recording_id] = recording_info

        logger.info(
            "[session_id=%s] Ses kaydı başlatıldı: recording_id=%s, "
            "start_ts=%.3f",
            session_id,
            recording_id,
            start_timestamp,
        )

        return recording_info

    async def stop_recording(
        self,
        recording_id: str,
    ) -> Dict[str, Any]:
        """
        Aktif ses kaydını durdurur.

        Args:
            recording_id : Durdurulacak kayıt kimliği.

        Returns:
            Kayıt sonuç bilgileri (dosya yolları, süre vb.).

        Raises:
            AudioRecordingError: Kayıt durdurulamazsa.
        """
        stop_timestamp = time.time()

        url = (
            f"{self.connector.base_url}/openvidu/api/recordings/stop/{recording_id}"
        )

        logger.info(
            "[recording_id=%s] Ses kaydı durduruluyor...",
            recording_id,
        )

        try:
            response = await self.connector._request("POST", url)
        except Exception as exc:
            raise AudioRecordingError(
                f"[recording_id={recording_id}] Ses kaydı durdurulamadı: {exc}"
            ) from exc

        # Kayıt meta verisini güncelle
        recording_info = self.active_recordings.get(recording_id, {})
        recording_info.update({
            "stop_timestamp": stop_timestamp,
            "stop_timestamp_iso": time.strftime(
                "%Y-%m-%dT%H:%M:%S%z", time.localtime(stop_timestamp)
            ),
            "status": "stopped",
            "duration_sec": stop_timestamp - recording_info.get("start_timestamp", stop_timestamp),
            "api_response_stop": response,
        })

        # Dosya yollarını oluştur
        session_id = recording_info.get("session_id", "unknown")
        participants = recording_info.get("participants", [])
        timestamp_str = str(int(recording_info.get("start_timestamp", time.time())))

        audio_files: Dict[str, str] = {}
        for participant in participants:
            filename = f"{session_id}_{participant}_{timestamp_str}.webm"
            filepath = str(self.output_dir / filename)
            audio_files[participant] = filepath

        recording_info["audio_files"] = audio_files

        logger.info(
            "[recording_id=%s] Ses kaydı durduruldu: duration=%.1fs, "
            "stop_ts=%.3f, dosya_sayısı=%d",
            recording_id,
            recording_info.get("duration_sec", 0),
            stop_timestamp,
            len(audio_files),
        )

        return recording_info

    async def get_recording_status(
        self,
        recording_id: str,
    ) -> Dict[str, Any]:
        """
        Kayıt durumunu OpenVidu API'sinden sorgular.

        Args:
            recording_id : Sorgulanacak kayıt kimliği.

        Returns:
            Kayıt durum bilgileri.
        """
        url = (
            f"{self.connector.base_url}/openvidu/api/recordings/{recording_id}"
        )

        logger.debug(
            "[recording_id=%s] Kayıt durumu sorgulanıyor...",
            recording_id,
        )

        return await self.connector._request("GET", url)

    def process_recordings(
        self,
        audio_files: Dict[str, str],
        output_dir: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Kaydedilen ses dosyalarını AudioStandardizer ile standart formata dönüştürür.

        Her WebM/Opus dosyasını 16kHz mono 16-bit PCM WAV'a dönüştürür.

        Args:
            audio_files : {participant_name: webm_file_path} sözlüğü.
            output_dir  : Standardize edilmiş WAV dosyalarının dizini.
                          None ise self.output_dir / "standardized" kullanılır.

        Returns:
            {participant_name: standardized_wav_path} sözlüğü.

        Raises:
            AudioRecordingError: Dönüştürme başarısızsa.
        """
        from module1_vad import AudioStandardizer

        standardizer = AudioStandardizer()
        std_dir = Path(output_dir or str(self.output_dir / "standardized"))
        std_dir.mkdir(parents=True, exist_ok=True)

        standardized_files: Dict[str, str] = {}

        for participant, webm_path in audio_files.items():
            webm_file = Path(webm_path)
            if not webm_file.exists():
                logger.warning(
                    "Ses dosyası bulunamadı, atlanıyor: %s", webm_path
                )
                continue

            wav_filename = webm_file.stem + ".wav"
            wav_path = std_dir / wav_filename

            logger.info(
                "AudioStandardizer çalıştırılıyor: %s → %s",
                webm_path,
                wav_path,
            )

            try:
                standardizer.standardize(webm_path, wav_path)
                standardized_files[participant] = str(wav_path)
                logger.info(
                    "Standardizasyon tamamlandı: %s → %s",
                    participant,
                    wav_path,
                )
            except Exception as exc:
                logger.error(
                    "Standardizasyon başarısız: %s → %s",
                    participant,
                    exc,
                )
                raise AudioRecordingError(
                    f"Ses standardizasyonu başarısız ({participant}): {exc}"
                ) from exc

        return standardized_files

    def get_expected_filenames(
        self,
        session_id: str,
        participants: List[str],
        timestamp: float,
    ) -> Dict[str, str]:
        """
        Beklenen ses dosyası yollarını üretir (henüz dosya oluşturulmadan).

        Args:
            session_id   : Oturum kimliği.
            participants : Katılımcı adları.
            timestamp    : Kayıt başlangıç zaman damgası.

        Returns:
            {participant_name: expected_file_path} sözlüğü.
        """
        timestamp_str = str(int(timestamp))
        result: Dict[str, str] = {}

        for participant in participants:
            filename = f"{session_id}_{participant}_{timestamp_str}.webm"
            result[participant] = str(self.output_dir / filename)

        return result

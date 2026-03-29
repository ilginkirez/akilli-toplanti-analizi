"""
pipeline_orchestrator.py
------------------------
Tüm OpenVidu entegrasyon bileşenlerini senkronize eden ana orkestratör.

Senkronizasyon akışı:
    1. OpenVidu session aç
    2. Audio recording başlat (INDIVIDUAL mod)
    3. Video recording başlat (COMPOSED mod)
    4. VAD realtime bus başlat
    5. base_timestamp = t=0 (tüm bileşenler için ortak)

Session kapandığında:
    stop recording → AudioStandardizer → MultiChannelVAD →
    RTTMWriter → session_report.json

Hata durumunda:
    partial RTTM kaydet, session raporuna hata logla.
"""

import asyncio
import logging
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from .openvidu_connector import OpenViduConnector
from .audio_recorder import AudioRecorder
from .video_recorder import VideoRecorder
from .realtime_bus import VADSessionManager
from .session_report_generator import SessionReportGenerator

logger = logging.getLogger("meeting_analyzer.pipeline")


class PipelineError(Exception):
    """Pipeline orkestrasyonu sırasında oluşan hatalar için özel exception."""
    pass


class SessionState:
    """
    Bir oturumun pipeline durumunu takip eden veri sınıfı.

    Attributes:
        session_id       : Oturum kimliği.
        participants     : Katılımcı adları.
        base_timestamp   : Senkronizasyon başlangıç zamanı (Unix epoch).
        audio_recording_id : Ses kaydı kimliği.
        video_recording_id : Video kaydı kimliği.
        status           : Pipeline durumu ("initializing", "recording", "processing", "completed", "error").
        errors           : Oluşan hata listesi.
    """

    def __init__(self, session_id: str, participants: List[str]) -> None:
        self.session_id = session_id
        self.participants = participants
        self.base_timestamp: float = 0.0
        self.audio_recording_id: Optional[str] = None
        self.video_recording_id: Optional[str] = None
        self.audio_files: Dict[str, str] = {}
        self.standardized_files: Dict[str, str] = {}
        self.video_path: Optional[str] = None
        self.rttm_path: Optional[str] = None
        self.report_path: Optional[str] = None
        self.status: str = "initializing"
        self.errors: List[str] = []
        self.segments: List[dict] = []

    def to_dict(self) -> Dict[str, Any]:
        """Durumu sözlük olarak döndürür."""
        return {
            "session_id": self.session_id,
            "participants": self.participants,
            "base_timestamp": self.base_timestamp,
            "audio_recording_id": self.audio_recording_id,
            "video_recording_id": self.video_recording_id,
            "status": self.status,
            "errors": self.errors,
        }


class PipelineOrchestrator:
    """
    OpenVidu oturum pipeline'ını yöneten orkestratör.

    Tüm bileşenleri koordine eder:
        - OpenViduConnector: Oturum yönetimi
        - AudioRecorder: Ses kaydı
        - VideoRecorder: Video kaydı
        - VADSessionManager: Gerçek zamanlı VAD yayını
        - SessionReportGenerator: Rapor üretimi

    Attributes:
        connector      : OpenViduConnector örneği.
        audio_recorder : AudioRecorder örneği.
        video_recorder : VideoRecorder örneği.
        vad_manager    : VADSessionManager örneği.
        report_gen     : SessionReportGenerator örneği.
        sessions       : Aktif oturum durumları.
    """

    def __init__(
        self,
        connector: OpenViduConnector,
        audio_recorder: AudioRecorder,
        video_recorder: VideoRecorder,
        vad_manager: VADSessionManager,
        output_dir: Optional[str] = None,
    ) -> None:
        """
        PipelineOrchestrator örneği oluşturur.

        Args:
            connector      : OpenViduConnector örneği.
            audio_recorder : AudioRecorder örneği.
            video_recorder : VideoRecorder örneği.
            vad_manager    : VADSessionManager örneği.
            output_dir     : Çıktı dizini (RTTM, rapor vb.).
        """
        self.connector = connector
        self.audio_recorder = audio_recorder
        self.video_recorder = video_recorder
        self.vad_manager = vad_manager
        self.report_gen = SessionReportGenerator(output_dir=output_dir)

        self.output_dir = Path(output_dir or "./recordings")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Aktif oturum durumları: {session_id: SessionState}
        self.sessions: Dict[str, SessionState] = {}

        logger.info(
            "PipelineOrchestrator başlatıldı: output_dir=%s",
            self.output_dir,
        )

    # ------------------------------------------------------------------
    # Ana API
    # ------------------------------------------------------------------

    async def start_session(
        self,
        session_id: str,
        participants: List[str],
    ) -> Dict[str, Any]:
        """
        Yeni bir oturum başlatır ve tüm kayıtları senkronize eder.

        Akış:
            1. OpenVidu session oluştur
            2. Her katılımcı için bağlantı token'ı üret
            3. base_timestamp belirle (t=0)
            4. Audio recording başlat (INDIVIDUAL)
            5. Video recording başlat (COMPOSED)
            6. VAD realtime bus oturumu oluştur

        Args:
            session_id   : Oturum kimliği.
            participants : Katılımcı adları listesi.

        Returns:
            Oturum bilgileri (token'lar dahil).

        Raises:
            PipelineError: Oturum başlatılamazsa.
        """
        state = SessionState(session_id, participants)
        self.sessions[session_id] = state

        logger.info(
            "[session_id=%s] Pipeline başlatılıyor: participants=%s",
            session_id,
            participants,
        )

        try:
            # 1. OpenVidu session oluştur
            session_props = {
                "mediaMode": "ROUTED",
                "recordingMode": "MANUAL",
            }
            await self.connector.create_session(
                session_id=session_id,
                properties=session_props,
            )

            # 2. Her katılımcı için token üret
            tokens: Dict[str, str] = {}
            for participant in participants:
                conn_info = await self.connector.create_connection(
                    session_id=session_id,
                    participant_name=participant,
                    role="PUBLISHER",
                )
                tokens[participant] = conn_info.get("token", "")

            # 3. Senkronizasyon noktası — tüm kayıtlar için ortak t=0
            state.base_timestamp = time.time()

            # 4. Audio recording başlat
            audio_info = await self.audio_recorder.start_recording(
                session_id=session_id,
                participants=participants,
            )
            state.audio_recording_id = audio_info.get("recording_id")

            # 5. Video recording başlat
            video_info = await self.video_recorder.start_recording(
                session_id=session_id,
                base_timestamp=state.base_timestamp,
            )
            state.video_recording_id = video_info.get("recording_id")
            state.video_path = video_info.get("video_path")

            # 6. VAD realtime bus oturumu oluştur
            self.vad_manager.create_session(session_id, participants)

            state.status = "recording"

            logger.info(
                "[session_id=%s] Pipeline başlatıldı: base_ts=%.3f, "
                "audio_rec=%s, video_rec=%s",
                session_id,
                state.base_timestamp,
                state.audio_recording_id,
                state.video_recording_id,
            )

            return {
                "session_id": session_id,
                "participants": participants,
                "tokens": tokens,
                "base_timestamp": state.base_timestamp,
                "audio_recording_id": state.audio_recording_id,
                "video_recording_id": state.video_recording_id,
                "status": state.status,
            }

        except Exception as exc:
            error_msg = f"Pipeline başlatma hatası: {exc}"
            state.errors.append(error_msg)
            state.status = "error"
            logger.error("[session_id=%s] %s", session_id, error_msg)
            raise PipelineError(error_msg) from exc

    async def stop_session(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Oturumu durdurur ve post-processing pipeline'ını çalıştırır.

        Akış:
            1. Audio recording durdur
            2. Video recording durdur
            3. VAD bus oturumunu kapat
            4. AudioStandardizer → MultiChannelVAD → RTTMWriter
            5. Session raporu üret

        Hata durumunda: partial RTTM kaydet, raporuna hata logla.

        Args:
            session_id : Durdurulacak oturum kimliği.

        Returns:
            Session raporu.
        """
        state = self.sessions.get(session_id)
        if not state:
            raise PipelineError(
                f"[session_id={session_id}] Oturum bulunamadı."
            )

        logger.info(
            "[session_id=%s] Pipeline durduruluyor...",
            session_id,
        )

        state.status = "processing"

        # 1. Audio recording durdur
        if state.audio_recording_id:
            try:
                audio_result = await self.audio_recorder.stop_recording(
                    state.audio_recording_id
                )
                state.audio_files = audio_result.get("audio_files", {})
            except Exception as exc:
                error_msg = f"Audio kaydı durdurma hatası: {exc}"
                state.errors.append(error_msg)
                logger.error("[session_id=%s] %s", session_id, error_msg)

        # 2. Video recording durdur
        if state.video_recording_id:
            try:
                video_result = await self.video_recorder.stop_recording(
                    state.video_recording_id
                )
                state.video_path = video_result.get("video_path")
            except Exception as exc:
                error_msg = f"Video kaydı durdurma hatası: {exc}"
                state.errors.append(error_msg)
                logger.error("[session_id=%s] %s", session_id, error_msg)

        # 3. VAD bus oturumunu kapat
        self.vad_manager.close_session(session_id)

        # 4. Post-processing pipeline
        try:
            await self._run_vad_pipeline(session_id)
        except Exception as exc:
            error_msg = f"VAD pipeline hatası: {exc}\n{traceback.format_exc()}"
            state.errors.append(error_msg)
            logger.error("[session_id=%s] %s", session_id, error_msg)

        # 5. OpenVidu session kapat
        try:
            await self.connector.close_session(session_id)
        except Exception as exc:
            error_msg = f"OpenVidu session kapatma hatası: {exc}"
            state.errors.append(error_msg)
            logger.error("[session_id=%s] %s", session_id, error_msg)

        # 6. Session raporu üret
        report = self._generate_report(session_id)
        state.report_path = report.get("report_path")
        state.status = "completed" if not state.errors else "completed_with_errors"

        logger.info(
            "[session_id=%s] Pipeline tamamlandı: status=%s, errors=%d",
            session_id,
            state.status,
            len(state.errors),
        )

        return report

    # ------------------------------------------------------------------
    # Dahili Pipeline
    # ------------------------------------------------------------------

    async def _run_vad_pipeline(self, session_id: str) -> None:
        """
        AudioStandardizer → MultiChannelVAD → RTTMWriter pipeline'ını çalıştırır.

        Args:
            session_id : Oturum kimliği.

        Raises:
            PipelineError: Pipeline herhangi bir aşamada başarısız olursa.
        """
        state = self.sessions[session_id]

        logger.info(
            "[session_id=%s] VAD pipeline başlatılıyor: %d ses dosyası",
            session_id,
            len(state.audio_files),
        )

        if not state.audio_files:
            logger.warning(
                "[session_id=%s] Ses dosyası yok, VAD pipeline atlanıyor.",
                session_id,
            )
            return

        # Adım 1: AudioStandardizer ile dönüştürme
        try:
            standardized = self.audio_recorder.process_recordings(
                state.audio_files,
                output_dir=str(self.output_dir / session_id / "standardized"),
            )
            state.standardized_files = standardized
        except Exception as exc:
            error_msg = f"Audio standardizasyon hatası: {exc}"
            state.errors.append(error_msg)
            logger.error("[session_id=%s] %s", session_id, error_msg)
            # Partial bilgiyle devam et
            return

        # Adım 2: MultiChannelVAD ile analiz
        try:
            import numpy as np
            from module1_vad import MultiChannelVAD, AudioStandardizer

            mcvad = MultiChannelVAD()
            standardizer = AudioStandardizer()

            # Standardize edilmiş WAV dosyalarını yükle
            channel_audio: Dict[str, np.ndarray] = {}
            for participant, wav_path in standardized.items():
                audio = standardizer.load_and_standardize(wav_path)
                channel_audio[participant] = audio

            if channel_audio:
                segments = mcvad.process(channel_audio)
                state.segments = segments

                logger.info(
                    "[session_id=%s] VAD analizi tamamlandı: %d segment",
                    session_id,
                    len(segments),
                )
            else:
                logger.warning(
                    "[session_id=%s] Yüklenecek ses kanalı yok.",
                    session_id,
                )
                return
        except Exception as exc:
            error_msg = f"MultiChannelVAD hatası: {exc}"
            state.errors.append(error_msg)
            logger.error("[session_id=%s] %s", session_id, error_msg)
            return

        # Adım 3: RTTMWriter ile RTTM dosyası üret
        try:
            from module1_vad import RTTMWriter

            rttm_writer = RTTMWriter(recording_id=session_id)
            rttm_path = self.output_dir / session_id / f"{session_id}.rttm"
            rttm_path.parent.mkdir(parents=True, exist_ok=True)

            rttm_writer.write(state.segments, rttm_path, recording_id=session_id)
            state.rttm_path = str(rttm_path)

            logger.info(
                "[session_id=%s] RTTM dosyası yazıldı: %s",
                session_id,
                rttm_path,
            )
        except Exception as exc:
            error_msg = f"RTTM yazma hatası: {exc}"
            state.errors.append(error_msg)
            logger.error("[session_id=%s] %s", session_id, error_msg)

    def _generate_report(self, session_id: str) -> Dict[str, Any]:
        """
        Session raporu üretir.

        Args:
            session_id : Oturum kimliği.

        Returns:
            Üretilen rapor sözlüğü.
        """
        state = self.sessions[session_id]

        report_path = str(
            self.output_dir / session_id / f"{session_id}_report.json"
        )

        report = self.report_gen.generate(
            session_id=session_id,
            base_timestamp=state.base_timestamp,
            participants=state.participants,
            segments=state.segments,
            rttm_path=state.rttm_path,
            video_path=state.video_path,
            audio_files=state.audio_files,
            errors=state.errors if state.errors else None,
            output_path=report_path,
        )

        logger.info(
            "[session_id=%s] Session raporu üretildi: %s",
            session_id,
            report_path,
        )

        return report

    # ------------------------------------------------------------------
    # Yardımcı Metodlar
    # ------------------------------------------------------------------

    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Oturum durumunu sorgular.

        Args:
            session_id : Oturum kimliği.

        Returns:
            Oturum durumu veya None.
        """
        state = self.sessions.get(session_id)
        return state.to_dict() if state else None

    def get_active_sessions(self) -> List[str]:
        """Aktif oturum kimliklerini döndürür."""
        return [
            sid for sid, state in self.sessions.items()
            if state.status == "recording"
        ]

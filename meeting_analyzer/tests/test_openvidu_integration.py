"""
test_openvidu_integration.py
----------------------------
OpenVidu entegrasyon modülleri için mock tabanlı birim testleri.

Gerçek OpenVidu sunucusu gerektirmez — tüm HTTP çağrıları mocklanır.

Test sınıfları:
    - TestOpenViduConnector   : Session CRUD, token üretimi, hata senaryoları
    - TestAudioRecorder       : Recording start/stop, AudioStandardizer entegrasyonu
    - TestVideoRecorder       : Composite recording, zaman senkronizasyonu
    - TestRealtimeBus         : WebSocket mesaj formatı, session manager
    - TestPipelineOrchestrator: End-to-end pipeline, hata kurtarma
    - TestSessionReportGenerator: Rapor formatı, hesaplama doğruluğu
"""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# Proje kökünü path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ═══════════════════════════════════════════════════════════════════════
# Test Fixtures
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_env(monkeypatch):
    """OpenVidu ortam değişkenlerini ayarlar."""
    monkeypatch.setenv("OPENVIDU_URL", "https://localhost:4443")
    monkeypatch.setenv("OPENVIDU_SECRET", "TEST_SECRET")
    monkeypatch.setenv("SSL_VERIFY", "false")
    monkeypatch.setenv("RECORDING_OUTPUT_DIR", "./test_recordings")


@pytest.fixture
def sample_segments():
    """Test için örnek segment listesi döndürür."""
    return [
        {
            "speaker": "Alice",
            "start": 0.0,
            "end": 5.0,
            "duration": 5.0,
            "type": "single",
            "speakers": ["Alice"],
        },
        {
            "speaker": "overlap",
            "start": 5.0,
            "end": 6.5,
            "duration": 1.5,
            "type": "overlap",
            "speakers": ["Alice", "Bob"],
        },
        {
            "speaker": "Bob",
            "start": 6.5,
            "end": 12.0,
            "duration": 5.5,
            "type": "single",
            "speakers": ["Bob"],
        },
        {
            "speaker": "Alice",
            "start": 12.0,
            "end": 15.0,
            "duration": 3.0,
            "type": "single",
            "speakers": ["Alice"],
        },
    ]


@pytest.fixture
def temp_output_dir():
    """Geçici çıktı dizini oluşturur ve temizler."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ═══════════════════════════════════════════════════════════════════════
# 1. TestOpenViduConnector
# ═══════════════════════════════════════════════════════════════════════

class TestOpenViduConnector:
    """OpenViduConnector sınıfı için birim testleri."""

    def test_init_with_params(self):
        """Parametrelerle başlatma testi."""
        from src.openvidu_connector import OpenViduConnector

        connector = OpenViduConnector(
            base_url="https://test:4443",
            secret="my_secret",
            verify_ssl=False,
        )
        assert connector.base_url == "https://test:4443"
        assert connector.secret == "my_secret"
        assert connector.verify_ssl is False

    def test_init_missing_url_raises(self):
        """URL eksikse ValueError fırlatma testi."""
        from src.openvidu_connector import OpenViduConnector

        with pytest.raises(ValueError, match="OpenVidu URL"):
            OpenViduConnector(base_url="", secret="sec")

    def test_init_missing_secret_raises(self):
        """Secret eksikse ValueError fırlatma testi."""
        from src.openvidu_connector import OpenViduConnector

        with pytest.raises(ValueError, match="OpenVidu secret"):
            OpenViduConnector(base_url="https://test:4443", secret="")

    @pytest.mark.asyncio
    async def test_create_session(self):
        """Oturum oluşturma testi (mock HTTP)."""
        from src.openvidu_connector import OpenViduConnector

        connector = OpenViduConnector(
            base_url="https://test:4443",
            secret="test_secret",
            verify_ssl=False,
        )

        mock_response = {
            "id": "test-session-123",
            "createdAt": 1234567890,
            "mediaMode": "ROUTED",
        }

        connector._request = AsyncMock(return_value=mock_response)

        result = await connector.create_session(session_id="test-session-123")

        assert result["id"] == "test-session-123"
        connector._request.assert_called_once_with(
            "POST",
            "https://test:4443/openvidu/api/sessions",
            json_data={"customSessionId": "test-session-123"},
        )

    @pytest.mark.asyncio
    async def test_create_connection(self):
        """Katılımcı bağlantısı ve token üretimi testi."""
        from src.openvidu_connector import OpenViduConnector

        connector = OpenViduConnector(
            base_url="https://test:4443",
            secret="test_secret",
            verify_ssl=False,
        )

        mock_response = {
            "id": "conn-abc",
            "token": "wss://test:4443?sessionId=s1&token=tok123",
            "role": "PUBLISHER",
        }

        connector._request = AsyncMock(return_value=mock_response)

        result = await connector.create_connection(
            session_id="s1",
            participant_name="Alice",
            role="PUBLISHER",
        )

        assert "token" in result
        assert result["role"] == "PUBLISHER"
        connector._request.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_session(self):
        """Oturum kapatma testi."""
        from src.openvidu_connector import OpenViduConnector

        connector = OpenViduConnector(
            base_url="https://test:4443",
            secret="test_secret",
            verify_ssl=False,
        )

        # close_session DELETE isteği kullanır — özel mock gerekir
        mock_resp = AsyncMock()
        mock_resp.status = 204
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.delete = MagicMock(return_value=mock_resp)
        mock_session.closed = False

        connector._session = mock_session

        result = await connector.close_session("test-session")
        assert result is True


# ═══════════════════════════════════════════════════════════════════════
# 2. TestAudioRecorder
# ═══════════════════════════════════════════════════════════════════════

class TestAudioRecorder:
    """AudioRecorder sınıfı için birim testleri."""

    def test_init(self, temp_output_dir):
        """Başlatma testi."""
        from src.audio_recorder import AudioRecorder

        mock_connector = MagicMock()
        recorder = AudioRecorder(
            connector=mock_connector,
            output_dir=temp_output_dir,
        )

        assert recorder.output_dir == Path(temp_output_dir)
        assert len(recorder.active_recordings) == 0

    @pytest.mark.asyncio
    async def test_start_recording(self, temp_output_dir):
        """Ses kaydı başlatma testi."""
        from src.audio_recorder import AudioRecorder

        mock_connector = MagicMock()
        mock_connector.base_url = "https://test:4443"
        mock_connector._request = AsyncMock(return_value={
            "id": "rec-audio-001",
            "status": "started",
        })

        recorder = AudioRecorder(
            connector=mock_connector,
            output_dir=temp_output_dir,
        )

        result = await recorder.start_recording(
            session_id="session-1",
            participants=["Alice", "Bob"],
        )

        assert result["recording_id"] == "rec-audio-001"
        assert result["session_id"] == "session-1"
        assert result["status"] == "started"
        assert "start_timestamp" in result
        assert "rec-audio-001" in recorder.active_recordings

    @pytest.mark.asyncio
    async def test_stop_recording(self, temp_output_dir):
        """Ses kaydı durdurma testi."""
        from src.audio_recorder import AudioRecorder

        mock_connector = MagicMock()
        mock_connector.base_url = "https://test:4443"
        mock_connector._request = AsyncMock(return_value={
            "id": "rec-audio-001",
            "status": "stopped",
        })

        recorder = AudioRecorder(
            connector=mock_connector,
            output_dir=temp_output_dir,
        )

        # Önce kayıt bilgisini ekle
        recorder.active_recordings["rec-audio-001"] = {
            "recording_id": "rec-audio-001",
            "session_id": "session-1",
            "participants": ["Alice", "Bob"],
            "start_timestamp": time.time() - 60,
            "status": "started",
        }

        result = await recorder.stop_recording("rec-audio-001")

        assert result["status"] == "stopped"
        assert "stop_timestamp" in result
        assert "duration_sec" in result
        assert "audio_files" in result
        assert "Alice" in result["audio_files"]
        assert "Bob" in result["audio_files"]

    def test_expected_filenames(self, temp_output_dir):
        """Dosya adı formatı testi."""
        from src.audio_recorder import AudioRecorder

        mock_connector = MagicMock()
        recorder = AudioRecorder(
            connector=mock_connector,
            output_dir=temp_output_dir,
        )

        ts = 1711234567.0
        filenames = recorder.get_expected_filenames(
            session_id="session-1",
            participants=["Alice", "Bob"],
            timestamp=ts,
        )

        assert "Alice" in filenames
        assert "Bob" in filenames
        assert "session-1_Alice_1711234567" in filenames["Alice"]
        assert filenames["Alice"].endswith(".webm")


# ═══════════════════════════════════════════════════════════════════════
# 3. TestVideoRecorder
# ═══════════════════════════════════════════════════════════════════════

class TestVideoRecorder:
    """VideoRecorder sınıfı için birim testleri."""

    def test_init_defaults(self, temp_output_dir):
        """Varsayılan parametrelerle başlatma testi."""
        from src.video_recorder import VideoRecorder

        mock_connector = MagicMock()
        recorder = VideoRecorder(
            connector=mock_connector,
            output_dir=temp_output_dir,
        )

        assert recorder.resolution == "1280x720"
        assert recorder.frame_rate == 30

    @pytest.mark.asyncio
    async def test_start_recording(self, temp_output_dir):
        """Composite video kaydı başlatma testi."""
        from src.video_recorder import VideoRecorder

        mock_connector = MagicMock()
        mock_connector.base_url = "https://test:4443"
        mock_connector._request = AsyncMock(return_value={
            "id": "rec-video-001",
            "status": "started",
        })

        recorder = VideoRecorder(
            connector=mock_connector,
            output_dir=temp_output_dir,
        )

        base_ts = 1711234567.0
        result = await recorder.start_recording(
            session_id="session-1",
            base_timestamp=base_ts,
        )

        assert result["recording_id"] == "rec-video-001"
        assert result["output_mode"] == "COMPOSED"
        assert result["resolution"] == "1280x720"
        assert result["base_timestamp"] == base_ts
        assert "composite" in result["video_path"]

        # API isteği doğrulama
        call_args = mock_connector._request.call_args
        payload = call_args.kwargs.get("json_data") or call_args[1].get("json_data")
        assert payload["outputMode"] == "COMPOSED"
        assert payload["resolution"] == "1280x720"
        assert payload["frameRate"] == 30

    @pytest.mark.asyncio
    async def test_stop_recording(self, temp_output_dir):
        """Video kaydı durdurma testi."""
        from src.video_recorder import VideoRecorder

        mock_connector = MagicMock()
        mock_connector.base_url = "https://test:4443"
        mock_connector._request = AsyncMock(return_value={
            "id": "rec-video-001",
            "status": "stopped",
        })

        recorder = VideoRecorder(
            connector=mock_connector,
            output_dir=temp_output_dir,
        )

        recorder.active_recordings["rec-video-001"] = {
            "recording_id": "rec-video-001",
            "start_timestamp": time.time() - 60,
            "video_path": str(Path(temp_output_dir) / "test_composite.webm"),
        }

        result = await recorder.stop_recording("rec-video-001")

        assert result["status"] == "stopped"
        assert "duration_sec" in result

    def test_sync_offset(self, temp_output_dir):
        """Zaman senkronizasyonu testi."""
        from src.video_recorder import VideoRecorder

        mock_connector = MagicMock()
        recorder = VideoRecorder(
            connector=mock_connector,
            output_dir=temp_output_dir,
        )

        base_ts = 1711234567.123
        recorder.active_recordings["rec-001"] = {
            "base_timestamp": base_ts,
        }

        offset = recorder.get_sync_offset("rec-001")
        assert offset == base_ts


# ═══════════════════════════════════════════════════════════════════════
# 4. TestRealtimeBus
# ═══════════════════════════════════════════════════════════════════════

class TestRealtimeBus:
    """RealtimeBus ve VADSessionManager için birim testleri."""

    def test_create_session(self):
        """VAD oturumu oluşturma testi."""
        from src.realtime_bus import VADSessionManager

        manager = VADSessionManager()
        manager.create_session("s1", ["Alice", "Bob"])

        assert "s1" in manager._sessions
        session = manager._sessions["s1"]
        assert session["active"] is True
        assert len(session["vad_state"]["speakers"]) == 2
        assert "Alice" in session["vad_state"]["speakers"]
        assert "Bob" in session["vad_state"]["speakers"]

    def test_update_vad_state(self):
        """VAD durum güncelleme testi."""
        from src.realtime_bus import VADSessionManager

        manager = VADSessionManager()
        manager.create_session("s1", ["Alice", "Bob"])

        speakers = {
            "Alice": {"speaking": True, "energy": 0.043, "overlap": False},
            "Bob": {"speaking": False, "energy": 0.002, "overlap": False},
        }

        manager.update_vad_state("s1", speakers, overlap_active=False)

        state = manager._sessions["s1"]["vad_state"]
        assert state["speakers"]["Alice"]["speaking"] is True
        assert state["speakers"]["Bob"]["speaking"] is False
        assert state["overlap_active"] is False
        assert state["timestamp_ms"] > 0

    def test_close_session(self):
        """VAD oturumu kapatma testi."""
        from src.realtime_bus import VADSessionManager

        manager = VADSessionManager()
        manager.create_session("s1", ["Alice"])

        assert manager._sessions["s1"]["active"] is True

        manager.close_session("s1")

        assert manager._sessions["s1"]["active"] is False

    def test_vad_message_format(self):
        """VAD broadcast mesaj formatı doğrulama testi."""
        from src.realtime_bus import VADSessionManager

        manager = VADSessionManager()
        manager.create_session("s1", ["Alice", "Bob"])

        speakers = {
            "Alice": {"speaking": True, "energy": 0.043, "overlap": False},
            "Bob": {"speaking": False, "energy": 0.002, "overlap": False},
        }
        manager.update_vad_state("s1", speakers)

        state = manager._sessions["s1"]["vad_state"]

        # JSON serileştirme kontrolü
        json_str = json.dumps(state)
        parsed = json.loads(json_str)

        assert "timestamp_ms" in parsed
        assert "speakers" in parsed
        assert "overlap_active" in parsed
        assert isinstance(parsed["speakers"]["Alice"]["speaking"], bool)
        assert isinstance(parsed["speakers"]["Alice"]["energy"], float)


# ═══════════════════════════════════════════════════════════════════════
# 5. TestPipelineOrchestrator
# ═══════════════════════════════════════════════════════════════════════

class TestPipelineOrchestrator:
    """PipelineOrchestrator sınıfı için birim testleri."""

    @pytest.mark.asyncio
    async def test_start_session(self, temp_output_dir):
        """Pipeline oturum başlatma testi."""
        from src.pipeline_orchestrator import PipelineOrchestrator
        from src.realtime_bus import VADSessionManager

        # Mock bileşenler
        mock_connector = AsyncMock()
        mock_connector.create_session = AsyncMock(return_value={
            "id": "test-session",
        })
        mock_connector.create_connection = AsyncMock(return_value={
            "token": "wss://test/token-alice",
        })

        mock_audio = AsyncMock()
        mock_audio.start_recording = AsyncMock(return_value={
            "recording_id": "rec-audio-001",
        })

        mock_video = AsyncMock()
        mock_video.start_recording = AsyncMock(return_value={
            "recording_id": "rec-video-001",
            "video_path": str(Path(temp_output_dir) / "composite.webm"),
        })

        vad_manager = VADSessionManager()

        orchestrator = PipelineOrchestrator(
            connector=mock_connector,
            audio_recorder=mock_audio,
            video_recorder=mock_video,
            vad_manager=vad_manager,
            output_dir=temp_output_dir,
        )

        result = await orchestrator.start_session(
            session_id="test-session",
            participants=["Alice", "Bob"],
        )

        assert result["session_id"] == "test-session"
        assert result["status"] == "recording"
        assert "Alice" in result["tokens"]
        assert result["audio_recording_id"] == "rec-audio-001"
        assert result["video_recording_id"] == "rec-video-001"

        # VAD oturumu oluşturuldu mu?
        assert "test-session" in vad_manager._sessions

    @pytest.mark.asyncio
    async def test_stop_session(self, temp_output_dir, sample_segments):
        """Pipeline oturum durdurma ve post-processing testi."""
        from src.pipeline_orchestrator import PipelineOrchestrator, SessionState
        from src.realtime_bus import VADSessionManager

        mock_connector = AsyncMock()
        mock_connector.close_session = AsyncMock(return_value=True)

        mock_audio = AsyncMock()
        mock_audio.stop_recording = AsyncMock(return_value={
            "audio_files": {
                "Alice": str(Path(temp_output_dir) / "alice.webm"),
                "Bob": str(Path(temp_output_dir) / "bob.webm"),
            },
        })
        mock_audio.process_recordings = MagicMock(return_value={})

        mock_video = AsyncMock()
        mock_video.stop_recording = AsyncMock(return_value={
            "video_path": str(Path(temp_output_dir) / "composite.webm"),
        })

        vad_manager = VADSessionManager()
        vad_manager.create_session("test-session", ["Alice", "Bob"])

        orchestrator = PipelineOrchestrator(
            connector=mock_connector,
            audio_recorder=mock_audio,
            video_recorder=mock_video,
            vad_manager=vad_manager,
            output_dir=temp_output_dir,
        )

        # Önceden session durumu ekle
        state = SessionState("test-session", ["Alice", "Bob"])
        state.base_timestamp = time.time() - 60
        state.audio_recording_id = "rec-audio-001"
        state.video_recording_id = "rec-video-001"
        state.status = "recording"
        orchestrator.sessions["test-session"] = state

        result = await orchestrator.stop_session("test-session")

        assert "session_id" in result
        assert result["session_id"] == "test-session"

        # Audio kaydı durduruldu mu?
        mock_audio.stop_recording.assert_called_once_with("rec-audio-001")

        # Video kaydı durduruldu mu?
        mock_video.stop_recording.assert_called_once_with("rec-video-001")

    @pytest.mark.asyncio
    async def test_start_session_error_handling(self, temp_output_dir):
        """Pipeline hata kurtarma testi."""
        from src.pipeline_orchestrator import PipelineOrchestrator, PipelineError
        from src.realtime_bus import VADSessionManager

        mock_connector = AsyncMock()
        mock_connector.create_session = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        mock_audio = AsyncMock()
        mock_video = AsyncMock()
        vad_manager = VADSessionManager()

        orchestrator = PipelineOrchestrator(
            connector=mock_connector,
            audio_recorder=mock_audio,
            video_recorder=mock_video,
            vad_manager=vad_manager,
            output_dir=temp_output_dir,
        )

        with pytest.raises(PipelineError, match="Pipeline başlatma hatası"):
            await orchestrator.start_session("fail-session", ["Alice"])

        # Session durumu "error" olmalı
        state = orchestrator.sessions.get("fail-session")
        assert state is not None
        assert state.status == "error"
        assert len(state.errors) > 0

    def test_get_active_sessions(self, temp_output_dir):
        """Aktif oturum listesi testi."""
        from src.pipeline_orchestrator import PipelineOrchestrator, SessionState
        from src.realtime_bus import VADSessionManager

        orchestrator = PipelineOrchestrator(
            connector=MagicMock(),
            audio_recorder=MagicMock(),
            video_recorder=MagicMock(),
            vad_manager=VADSessionManager(),
            output_dir=temp_output_dir,
        )

        state1 = SessionState("s1", ["Alice"])
        state1.status = "recording"
        orchestrator.sessions["s1"] = state1

        state2 = SessionState("s2", ["Bob"])
        state2.status = "completed"
        orchestrator.sessions["s2"] = state2

        active = orchestrator.get_active_sessions()
        assert "s1" in active
        assert "s2" not in active


# ═══════════════════════════════════════════════════════════════════════
# 6. TestSessionReportGenerator
# ═══════════════════════════════════════════════════════════════════════

class TestSessionReportGenerator:
    """SessionReportGenerator sınıfı için birim testleri."""

    def test_generate_report(self, temp_output_dir, sample_segments):
        """Rapor üretme ve format doğrulama testi."""
        from src.session_report_generator import SessionReportGenerator

        gen = SessionReportGenerator(output_dir=temp_output_dir)

        base_ts = time.time() - 120  # 2 dakika önce

        report = gen.generate(
            session_id="test-session",
            base_timestamp=base_ts,
            participants=["Alice", "Bob"],
            segments=sample_segments,
            rttm_path="/path/to/test.rttm",
            video_path="/path/to/composite.webm",
            audio_files={
                "Alice": "/path/to/alice.webm",
                "Bob": "/path/to/bob.webm",
            },
        )

        # Zorunlu alanlar
        assert report["session_id"] == "test-session"
        assert "start_time" in report
        assert "end_time" in report
        assert "duration_sec" in report
        assert report["participants"] == ["Alice", "Bob"]
        assert "total_speaking_time" in report
        assert "overlap_duration_sec" in report
        assert "overlap_percentage" in report
        assert "der_score" in report
        assert report["rttm_path"] == "/path/to/test.rttm"
        assert report["video_path"] == "/path/to/composite.webm"
        assert "Alice" in report["audio_tracks"]
        assert "Bob" in report["audio_tracks"]
        assert report["status"] == "completed"

        # JSON dosyası oluşturuldu mu?
        assert "report_path" in report
        report_path = Path(report["report_path"])
        assert report_path.exists()

        # JSON okunaklı mı?
        with report_path.open("r") as fh:
            loaded = json.load(fh)
        assert loaded["session_id"] == "test-session"

    def test_speaking_time_calculation(self, sample_segments):
        """Konuşma süresi hesaplama testi."""
        from src.session_report_generator import SessionReportGenerator

        times = SessionReportGenerator._calculate_speaking_times(
            sample_segments,
            ["Alice", "Bob"],
        )

        # Alice: 5.0s (single) + 1.5s (overlap) + 3.0s (single) = 9.5s
        assert abs(times["Alice"] - 9.5) < 0.01

        # Bob: 1.5s (overlap) + 5.5s (single) = 7.0s
        assert abs(times["Bob"] - 7.0) < 0.01

    def test_overlap_duration_calculation(self, sample_segments):
        """Overlap süresi hesaplama testi."""
        from src.session_report_generator import SessionReportGenerator

        overlap = SessionReportGenerator._calculate_overlap_duration(sample_segments)

        # 1 adet overlap segmenti: 6.5 - 5.0 = 1.5s
        assert abs(overlap - 1.5) < 0.01

    def test_report_with_errors(self, temp_output_dir, sample_segments):
        """Hatalı rapor üretme testi."""
        from src.session_report_generator import SessionReportGenerator

        gen = SessionReportGenerator(output_dir=temp_output_dir)

        report = gen.generate(
            session_id="error-session",
            base_timestamp=time.time() - 30,
            participants=["Alice"],
            segments=[],
            errors=["Audio kaydı başarısız", "RTTM yazma hatası"],
        )

        assert report["status"] == "completed_with_errors"
        assert "errors" in report
        assert len(report["errors"]) == 2

    def test_empty_segments(self, temp_output_dir):
        """Boş segment listesi ile rapor testi."""
        from src.session_report_generator import SessionReportGenerator

        gen = SessionReportGenerator(output_dir=temp_output_dir)

        report = gen.generate(
            session_id="empty-session",
            base_timestamp=time.time(),
            participants=["Alice"],
            segments=[],
        )

        assert report["total_speaking_time"]["Alice"] == 0.0
        assert report["overlap_duration_sec"] == 0.0
        assert report["overlap_percentage"] == 0.0


# ═══════════════════════════════════════════════════════════════════════
# 7. Entegrasyon Testleri
# ═══════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Modüller arası entegrasyon testleri."""

    def test_connector_to_recorder_flow(self, temp_output_dir):
        """Connector → AudioRecorder akış testi."""
        from src.openvidu_connector import OpenViduConnector
        from src.audio_recorder import AudioRecorder

        connector = OpenViduConnector(
            base_url="https://test:4443",
            secret="test",
            verify_ssl=False,
        )

        recorder = AudioRecorder(
            connector=connector,
            output_dir=temp_output_dir,
        )

        # Beklenen dosya adlarını doğrula
        filenames = recorder.get_expected_filenames(
            "session-1", ["Alice", "Bob"], 1711234567.0
        )

        assert len(filenames) == 2
        for name, path in filenames.items():
            assert "session-1" in path
            assert name in path
            assert path.endswith(".webm")

    def test_video_recorder_path_generation(self, temp_output_dir):
        """VideoRecorder dosya yolu üretim testi."""
        from src.video_recorder import VideoRecorder

        connector = MagicMock()
        recorder = VideoRecorder(
            connector=connector,
            output_dir=temp_output_dir,
        )

        path = recorder.get_video_path("session-1", 1711234567.0)
        assert "session-1_composite_1711234567" in path
        assert path.endswith(".webm")

    def test_report_generator_with_real_segments(self, temp_output_dir):
        """Gerçekçi segment verileriyle rapor üretim testi."""
        from src.session_report_generator import SessionReportGenerator

        gen = SessionReportGenerator(output_dir=temp_output_dir)

        # 30 dakikalık toplantı simülasyonu
        segments = []
        t = 0.0
        speakers = ["Alice", "Bob", "Charlie"]

        for i in range(50):
            speaker_idx = i % len(speakers)
            duration = 2.0 + (i % 5) * 0.5

            segments.append({
                "speaker": speakers[speaker_idx],
                "start": round(t, 4),
                "end": round(t + duration, 4),
                "duration": round(duration, 4),
                "type": "single",
                "speakers": [speakers[speaker_idx]],
            })
            t += duration

            # Her 5. segmentte overlap ekle
            if i % 5 == 4 and i > 0:
                overlap_dur = 0.5
                segments.append({
                    "speaker": "overlap",
                    "start": round(t, 4),
                    "end": round(t + overlap_dur, 4),
                    "duration": round(overlap_dur, 4),
                    "type": "overlap",
                    "speakers": [
                        speakers[speaker_idx],
                        speakers[(speaker_idx + 1) % len(speakers)],
                    ],
                })
                t += overlap_dur

        report = gen.generate(
            session_id="meeting-sim",
            base_timestamp=time.time() - t,
            participants=speakers,
            segments=segments,
        )

        assert len(report["participants"]) == 3
        assert all(
            report["total_speaking_time"][s] > 0 for s in speakers
        )
        assert report["overlap_duration_sec"] > 0
        assert report["overlap_percentage"] > 0

        # Rapor dosyası oluşturuldu
        assert Path(report["report_path"]).exists()


class TestSessionRouter:
    """Sessions router için join/token akış testleri."""

    def test_create_token_ensures_session_and_storage(
        self, monkeypatch, tmp_path
    ):
        """Join-first akışında session önce hazırlanmalı ve storage oluşmalı."""
        from src.routers import sessions as sessions_router

        session_mock = AsyncMock(return_value={"id": "meeting-1"})
        token_mock = AsyncMock(return_value="wss://test/token-1")

        monkeypatch.setattr(
            sessions_router.openvidu_service, "create_session", session_mock
        )
        monkeypatch.setattr(
            sessions_router.openvidu_service, "create_token", token_mock
        )
        monkeypatch.setattr(sessions_router, "STORAGE_DIR", tmp_path)

        result = asyncio.run(
            sessions_router.create_token(
                {
                    "session_id": "meeting-1",
                    "display_name": "Alice",
                    "device_info": {
                        "device_type": "desktop",
                        "os": "windows",
                        "browser": "chrome",
                    },
                }
            )
        )

        assert result["token"] == "wss://test/token-1"
        assert result["session_id"] == "meeting-1"
        session_mock.assert_awaited_once_with("meeting-1")
        token_mock.assert_awaited_once_with("meeting-1", result["participant_id"])

        session_file = tmp_path / "meeting-1" / "session.json"
        assert session_file.exists()

        metadata = json.loads(session_file.read_text())
        assert metadata["session_id"] == "meeting-1"
        assert metadata["participants"][0]["display_name"] == "Alice"

    def test_create_token_fails_fast_when_session_prepare_fails(
        self, monkeypatch, tmp_path
    ):
        """Session oluşturma başarısızsa token isteğine geçilmemeli."""
        from fastapi import HTTPException
        from src.routers import sessions as sessions_router

        session_mock = AsyncMock(side_effect=Exception("session failed"))
        token_mock = AsyncMock()

        monkeypatch.setattr(
            sessions_router.openvidu_service, "create_session", session_mock
        )
        monkeypatch.setattr(
            sessions_router.openvidu_service, "create_token", token_mock
        )
        monkeypatch.setattr(sessions_router, "STORAGE_DIR", tmp_path)

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                sessions_router.create_token(
                    {"session_id": "meeting-2", "display_name": "Bob"}
                )
            )

        assert exc_info.value.status_code == 500
        assert "OpenVidu session could not be prepared" in exc_info.value.detail
        token_mock.assert_not_awaited()

"""
src
---
Meeting Analyzer — Multi-user online meeting data acquisition
and speaker-aware analytics platform.

Bu paket:
- OpenVidu Server ile REST API iletişimi (OpenViduConnector)
- Katılımcı bazlı ses kaydı (AudioRecorder)
- Olay kayıt sistemi (EventRegistry)
- Dataset oluşturucu (DatasetBuilder)
- Gerçek zamanlı VAD yayını (RealtimeBus)
- FastAPI backend sunucusu (server)
"""

from .openvidu_connector import OpenViduConnector
from .audio_recorder import AudioRecorder
from .event_registry import EventRegistry
from .dataset_builder import DatasetBuilder
from .realtime_bus import RealtimeBus, VADSessionManager

__all__ = [
    "OpenViduConnector",
    "AudioRecorder",
    "EventRegistry",
    "DatasetBuilder",
    "RealtimeBus",
    "VADSessionManager",
]

__version__ = "1.0.0"

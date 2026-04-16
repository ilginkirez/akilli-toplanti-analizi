"""
src
---
Meeting Analyzer - multi-user online meeting data acquisition
and speaker-aware analytics platform.

Bu paket:
- Olay kayit sistemi (EventRegistry)
- Dataset olusturucu (DatasetBuilder)
- Gercek zamanli VAD yayini (RealtimeBus)
- FastAPI backend sunucusu (server)
"""

from .dataset_builder import DatasetBuilder
from .event_registry import EventRegistry
from .realtime_bus import RealtimeBus, VADSessionManager

__all__ = [
    "EventRegistry",
    "DatasetBuilder",
    "RealtimeBus",
    "VADSessionManager",
]

__version__ = "1.0.0"

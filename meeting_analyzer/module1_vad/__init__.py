"""
module1_vad
-----------
Çok Kanallı Ses Ön İşleme ve VAD (Voice Activity Detection) modülü.

Bu paket:
- Ham ses kanallarını standardize eder (AudioStandardizer)
- Adaptif enerji tabanlı VAD uygular (EnergyVAD)
- Tüm kanalları eş zamanlı analiz eder (MultiChannelVAD)
- Sonuçları RTTM formatında dışa aktarır (RTTMWriter)
"""

from .audio_standardizer import AudioStandardizer
from .energy_vad import EnergyVAD
from .mcvad import MultiChannelVAD
from .rttm_writer import RTTMWriter
from . import config

__all__ = [
    "AudioStandardizer",
    "EnergyVAD",
    "MultiChannelVAD",
    "RTTMWriter",
    "config",
]

__version__ = "0.1.0"

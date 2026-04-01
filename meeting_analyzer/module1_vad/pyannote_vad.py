"""
pyannote_vad.py
---------------
Pyannote VAD (Neural VAD) tabanli per-kanal VAD sargisi (wrapper).
EnergyVAD ile ayni arayuzu saglar (VADResult) ama kararlari HuggingFace uzerinden
pyannote/segmentation-3.0 modeliyle alir.
"""

import os
import torch
import numpy as np

# PyTorch 2.6+ ve torchaudio <=2.5 uyuşmazlığı yası (AudioMetaData mock)
import torchaudio
if not hasattr(torchaudio, "AudioMetaData"):
    torchaudio.AudioMetaData = type("AudioMetaData", (), {})

from pyannote.audio import Model
from pyannote.audio.pipelines import VoiceActivityDetection

from .energy_vad import VADResult
from . import config

class PyannoteVAD:
    def __init__(self, sample_rate: int = 16000, hf_token: str = None):
        self.sample_rate = sample_rate
        self.frame_length_ms = config.FRAME_LENGTH_MS
        self.hop_length_ms = config.HOP_LENGTH_MS
        
        token = hf_token or os.environ.get("HF_TOKEN")
        if not token:
            raise ValueError("Pyannote VAD icin HuggingFace token gerekli. 'HF_TOKEN' ortam degiskenini ayarlayin.")
            
        print("Yukleniyor: pyannote/segmentation-3.0 ...")
        
        # huggingface_hub >= 0.22 icin use_auth_token yerine token kullanilir
        import os
        os.environ["HF_TOKEN"] = token
            
        try:
            self.model = Model.from_pretrained("pyannote/segmentation-3.0", token=token)
        except Exception:
            self.model = Model.from_pretrained("pyannote/segmentation-3.0", use_auth_token=token)
            
        self.vad_pipeline = VoiceActivityDetection(segmentation=self.model)
        
        # Pyannote hyperparams (VAD pipeline'i aktif etmek icin instantiate etmeliyiz)
        self.vad_pipeline.instantiate({
            "onset": 0.5,
            "offset": 0.5,
            "min_duration_on": 0.0,
            "min_duration_off": 0.0
        })

    def detect(self, audio_data: np.ndarray, sample_rate: int = None) -> VADResult:
        if sample_rate is None:
            sample_rate = self.sample_rate
            
        # Pyannote (1, T) seklinde tensor ister
        waveform = torch.from_numpy(audio_data).unsqueeze(0).float()
        
        # Pyannote pipeline cagirimi
        vad_segments = self.vad_pipeline({"waveform": waveform, "sample_rate": sample_rate})
        
        # Enerji dizisini her turlu olusturmaliyiz (IHM overlap dogrulamasi icin gerekli)
        frame_len = int(sample_rate * self.frame_length_ms / 1000)
        hop_len = int(sample_rate * self.hop_length_ms / 1000)
        
        n_samples = len(audio_data)
        n_frames = 1 + (n_samples - frame_len) // hop_len
        if n_frames < 0: n_frames = 0
        
        frame_energies = np.zeros(n_frames, dtype=np.float32)
        frame_times = np.zeros(n_frames, dtype=np.float64)
        frame_activity = np.zeros(n_frames, dtype=bool)
        
        # RMS enerji hesapla
        for i in range(n_frames):
            start_idx = i * hop_len
            end_idx = start_idx + frame_len
            frame = audio_data[start_idx:end_idx]
            rms = np.sqrt(np.mean(frame**2) + 1e-10)
            frame_energies[i] = rms
            frame_times[i] = start_idx / sample_rate
            
        # Pyannote segmentlerini (start, end saniye olarak) frame maskesine donustur
        for segment in vad_segments.itersegments():
            start_f = int((segment.start * sample_rate) / hop_len)
            end_f = int((segment.end * sample_rate) / hop_len)
            
            # Sinirlari koru
            start_f = max(0, start_f)
            end_f = min(n_frames, end_f)
            
            frame_activity[start_f:end_f] = True
            
        # Thresholds yalandan, sadece EnergyVAD API'siyle uyumlu olmak icin sifir
        thresholds = np.zeros(n_frames, dtype=np.float32)
        
        return VADResult(
            frame_activity=frame_activity,
            frame_energies=frame_energies,
            thresholds=thresholds,
            frame_times=frame_times,
            spectral_flatness=None
        )

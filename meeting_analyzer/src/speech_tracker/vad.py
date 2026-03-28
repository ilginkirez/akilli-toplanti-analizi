import numpy as np
import soundfile as sf
from dataclasses import dataclass

SR = 16000
FRAME_MS = 25
HOP_MS = 10
FRAME_LEN = int(FRAME_MS * SR / 1000)
HOP_LEN = int(HOP_MS * SR / 1000)
MIN_SPEECH_MS = 300
MIN_SPEECH_FRAMES = int(MIN_SPEECH_MS / HOP_MS)
NOISE_PERCENTILE = 20
NOISE_MULT = 3.0

@dataclass
class SpeechSegment:
    participant_id: str
    begin_time: float
    end_time: float
    is_active: bool
    speech_duration: float
    overlap_flag: bool = False
    confidence: float = 1.0

def compute_rms_frames(audio: np.ndarray) -> np.ndarray:
    n = (len(audio) - FRAME_LEN) // HOP_LEN
    out = np.zeros(n, dtype=np.float32)
    for i in range(n):
        s = i * HOP_LEN
        out[i] = np.sqrt(np.mean(audio[s:s+FRAME_LEN]**2))
    return out

def apply_vad(energies: np.ndarray) -> np.ndarray:
    noise = np.percentile(energies, NOISE_PERCENTILE)
    thr = max(0.005, noise * NOISE_MULT)
    vad = energies > thr
    
    i = 0
    while i < len(vad):
        if vad[i]:
            j = i
            while j < len(vad) and vad[j]: j += 1
            if (j - i) < MIN_SPEECH_FRAMES:
                vad[i:j] = False
            i = j
        else:
            i += 1
    return vad

def compute_segments(wav_path: str) -> list[dict]:
    audio, _ = sf.read(wav_path, dtype='float32')
    if audio.ndim > 1:
        audio = audio.mean(axis=1) # stereo to mono
    energies = compute_rms_frames(audio)
    vad = apply_vad(energies)
    
    segments = []
    in_seg, start = False, 0.0
    
    for t in range(len(vad)):
        t_sec = t * HOP_MS / 1000
        if vad[t] and not in_seg:
            start = t_sec
            in_seg = True
        elif not vad[t] and in_seg:
            segments.append({"start": start, "end": t_sec})
            in_seg = False
    
    if in_seg:
        segments.append({"start": start, "end": len(vad) * HOP_MS / 1000})
    
    return segments

def detect_overlap(all_vads: dict[str, np.ndarray],
                   all_energies: dict[str, np.ndarray],
                   bleed_ratio: float = 0.15) -> np.ndarray:
    n = len(next(iter(all_vads.values())))
    overlap = np.zeros(n, dtype=bool)
    speakers = list(all_vads.keys())

    for t in range(n):
        active = [s for s in speakers if all_vads[s][t]]
        if len(active) < 2:
            continue
        max_e = max(all_energies[s][t] for s in active)
        real = [s for s in active
                if all_energies[s][t] >= max_e * bleed_ratio]
        if len(real) >= 2:
            overlap[t] = True

    return overlap

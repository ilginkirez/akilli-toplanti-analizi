import argparse
import glob
import os
import sys

import numpy as np

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from module1_vad.audio_standardizer import AudioStandardizer
from module1_vad.mcvad import MultiChannelVAD

def run_ablation(audio_dir: str):
    # Ses dosyalarını bul
    audio_files = glob.glob(os.path.join(audio_dir, "*.ogg"))
    if not audio_files:
        print(f"Ses dosyası bulunamadı: {audio_dir}")
        return

    print("Ses dosyaları yükleniyor...")
    standardizer = AudioStandardizer()
    channel_audio_dict = {}
    for af in audio_files:
        basename = os.path.basename(af)
        audio = standardizer.load_and_standardize(af)
        if audio.ndim != 1:
            audio = np.asarray(audio).reshape(-1)
        channel_audio_dict[basename] = audio
        print(f"  Yuklendi: {basename} ({len(audio)} sample)")

    # Test edilecek yerel(sliding_window) ve global(percentile) ağırlık çiftleri
    weight_pairs = [
        (1.0, 0.0), # Sadece kayan pencere (lokal)
        (0.7, 0.3), # Kendi kullandığın özgün değer (sweet spot)
        (0.5, 0.5), # Eşit ağırlık
        (0.3, 0.7), # Global ağırlıklı
        (0.0, 1.0)  # Sadece global persentil (klasik VAD)
    ]
    
    print("\n" + "="*95)
    print(f"{'Lokal Ağırlık':<15} {'Global Ağırlık':<15} {'Aktif Süre(s)':<15} {'Overlap Süre(s)':<17} {'Toplam Seg.':<15} {'Overlap Seg.':<15}")
    print("="*95)

    for lw, gw in weight_pairs:
        vad = MultiChannelVAD(local_weight=lw, global_weight=gw)
        activity_matrix, speaker_ids, frame_times = vad.get_activity_matrix(channel_audio_dict)
        segments = vad.process(channel_audio_dict)

        active_counts = np.sum(activity_matrix, axis=0)
        overlap_frames = np.sum(active_counts > 1)
        active_frames = np.sum(active_counts > 0)
        
        frame_duration = vad.vad.hop_duration
        overlap_duration = overlap_frames * frame_duration
        active_duration = active_frames * frame_duration

        total_seg = len(segments)
        overlap_seg = sum(1 for s in segments if s.get("type") == "overlap")

        print(f"{lw:<15.1f} {gw:<15.1f} {active_duration:<15.2f} {overlap_duration:<17.2f} {total_seg:<15} {overlap_seg:<15}")

    print("="*95)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio_dir", required=True)
    args = parser.parse_args()
    run_ablation(args.audio_dir)

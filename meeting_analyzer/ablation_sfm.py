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

    sfm_values = [0.4, 0.5, 0.6, 0.7, 0.8]
    
    print("\n" + "="*80)
    print(f"{'SFM Eşiği':<15} {'Aktif Süre(s)':<15} {'Overlap Süre(s)':<17} {'Toplam Seg.':<15} {'Overlap Seg.':<15}")
    print("="*80)

    for sfm in sfm_values:
        vad = MultiChannelVAD(sfm_threshold=sfm)
        activity_matrix, speaker_ids, frame_times = vad.get_activity_matrix(channel_audio_dict)
        segments = vad.process(channel_audio_dict)

        # activity_matrix: (num_speakers, num_frames)
        # overlap frames: frames where sum > 1
        active_counts = np.sum(activity_matrix, axis=0)
        overlap_frames = np.sum(active_counts > 1)
        active_frames = np.sum(active_counts > 0)
        
        frame_duration = vad.vad.hop_duration
        overlap_duration = overlap_frames * frame_duration
        active_duration = active_frames * frame_duration

        total_seg = len(segments)
        overlap_seg = sum(1 for s in segments if s.get("type") == "overlap")

        print(f"{sfm:<15.1f} {active_duration:<15.2f} {overlap_duration:<17.2f} {total_seg:<15} {overlap_seg:<15}")

    print("="*80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio_dir", required=True)
    args = parser.parse_args()
    run_ablation(args.audio_dir)

import argparse
import os
import sys
import glob

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    import jiwer
except ImportError:
    print("HATA: jiwer kütüphanesi eksik.")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
except ImportError:
    print("BILGI: matplotlib, seaborn veya numpy kurulu değil. Görselleştirme yapılamayacak.")

import src.services.ai_transcription as transcriber

def calculate_wer_cer(ref_text: str, hyp_text: str):
    ref = ref_text.strip().lower()
    hyp = hyp_text.strip().lower()
    if not ref:
        print("HATA: Referans metin boş olamaz.")
        return

    wer_score = jiwer.wer(ref, hyp)
    cer_score = jiwer.cer(ref, hyp)
    
    print("\n" + "="*50)
    print(" [AKADEMIK STT METRIKLERI (WHISPER)]")
    print("="*50)
    print(f"-> Referans: {len(ref.split())} kelime")
    print(f"-> Hipotez : {len(hyp.split())} kelime")
    print(f"* Word Error Rate (WER)     : {wer_score:.4f}")
    print(f"* Character Error Rate (CER): {cer_score:.4f}")
    print("="*50)

def generate_confidence_plot(audio_path_or_dir: str, is_dir=False, output_img="whisper_confidence_plot.png"):
    files_to_process = []
    if is_dir:
        for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac"):
            files_to_process.extend(glob.glob(os.path.join(audio_path_or_dir, "**", ext), recursive=True))
        print(f"[{audio_path_or_dir}] klasöründe {len(files_to_process)} adet ses dosyası saptandı. Toplu analiz başlıyor...")
    else:
        files_to_process = [audio_path_or_dir]

    logprobs = []
    no_speech_probs = []
    
    for f_path in files_to_process:
        if not os.path.exists(f_path):
            continue
        processed_path = transcriber._preprocess_audio(f_path)
        is_temp = processed_path != f_path
        try:
            payload = transcriber._request_transcription(processed_path, language="tr")
            segments = payload.get("segments", [])
            for seg in segments:
                lp = transcriber._coerce_float(seg.get("avg_logprob"))
                nsp = transcriber._coerce_float(seg.get("no_speech_prob"))
                if lp is not None and nsp is not None:
                    logprobs.append(lp)
                    no_speech_probs.append(nsp)
        except Exception as e:
            print(f"Yapay Zeka Servis Hatası ({os.path.basename(f_path)}): {e}")
        finally:
            if is_temp and os.path.exists(processed_path):
                os.remove(processed_path)
                
    if not logprobs:
        print("UYARI: Modelden herhangi bir veri çekilemedi.")
        return

    n_count = len(logprobs)
    print(f"-> Basarili! Toplam n={n_count} adet segment noktasi cikarildi.")
            
    if 'plt' not in globals() or 'sns' not in globals():
        return

    # JITTER Ekleme (Noktaları ufak rastgele sarsma) ki üst üste binenler görünsün
    np.random.seed(42) # Sabit rastgelelik
    jittered_logprobs = np.array(logprobs) + np.random.normal(0, 0.05, n_count)
    jittered_nospeech = np.clip(np.array(no_speech_probs) + np.random.normal(0, 0.02, n_count), 0, 1)

    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x=jittered_logprobs, y=jittered_nospeech, alpha=0.6, color="#0052cc", s=80)
    
    min_logprob = transcriber.MIN_AVG_LOGPROB
    max_no_speech = transcriber.MAX_NO_SPEECH_PROB
    
    plt.axvline(x=min_logprob, color='red', linestyle='--', label=f'Kesin Logprob Siniri ({min_logprob})')
    plt.axhline(y=max_no_speech, color='orange', linestyle='--', label=f'Kesin No Speech Siniri ({max_no_speech})')
    plt.axvline(x=transcriber.RELAXED_MIN_AVG_LOGPROB, color='darkred', linestyle=':', label='Esnek LogProb')
    plt.axhline(y=transcriber.RELAXED_MAX_NO_SPEECH_PROB, color='darkorange', linestyle=':', label='Esnek NoSpeech')

    plt.title(f"Whisper Guven Skoru (n={n_count}) - Overplot Jitter Aktif", fontsize=14)
    plt.xlabel("Average Logprob", fontsize=11)
    plt.ylabel("No Speech Probability", fontsize=11)
    plt.legend(loc='best')
    plt.tight_layout()
    plt.savefig(output_img, dpi=300)
    print(f"\n[ TEZ ICIN GRAFIK HAZIR ]: '{output_img}' dosyasina n={n_count} noktali harita kaydedildi.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["wer", "plot"], required=True)
    parser.add_argument("--ref", type=str)
    parser.add_argument("--hyp", type=str)
    parser.add_argument("--audio", type=str, help="Tek dosya")
    parser.add_argument("--audio_dir", type=str, help="Klasordeki tum wav/mp3/ogg dosyalari okur")
    args = parser.parse_args()
    
    if args.mode == "wer":
        with open(args.ref, 'r', encoding='utf-8') as f:
            r = f.read()
        with open(args.hyp, 'r', encoding='utf-8') as f:
            h = f.read()
        calculate_wer_cer(r, h)
    elif args.mode == "plot":
        if args.audio_dir:
            generate_confidence_plot(args.audio_dir, is_dir=True)
        elif args.audio:
            generate_confidence_plot(args.audio, is_dir=False)
        else:
            print("HATA: --audio veya --audio_dir kosmalisiniz.")

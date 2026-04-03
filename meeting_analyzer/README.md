# Module 1 – Çok Kanallı Ses Ön İşleme ve VAD

## Genel Bakış

Bu modül **Akıllı Toplantı Analiz Sistemi**'nin ilk bileşenidir. Her katılımcının WebRTC (OpenVidu) üzerinden iletilen ham ses kanalını 16 kHz mono WAV formatına standardize eder; ardından adaptif enerji eşiği tabanlı bir VAD (Voice Activity Detection) algoritmasıyla hangi zaman diliminde kimin konuştuğunu belirler. Diyarizasyon, model yerine mimari ile çözülür: her kanal zaten bir kişiye aittir, bu modül yalnızca hangi kanalın ne zaman aktif olduğunu saptarken cross-channel bleed (mikrofon sızıntısı) gürültüsünü bastırır ve sonuçları standart RTTM formatında dışa aktarır.

---

## Kurulum

### Ön Koşullar

| Araç | Versiyon | Notlar |
|------|----------|--------|
| Python | ≥ 3.10 | `match/case` ve `|` union tipi için |
| FFmpeg | Herhangi | PATH'te bulunmalı (opsiyonel, PyDub fallback var) |

### Adımlar

```bash
# 1. Depoyu klonla / klasöre gir
cd meeting_analyzer

# 2. Sanal ortam oluştur (önerilir)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. FFmpeg'i kur (Windows)
# winget install Gyan.FFmpeg
# veya https://www.gyan.dev/ffmpeg/builds/ adresinden indirin.
```

---

## Kullanım Örneği

```python
import numpy as np
from module1_vad import AudioStandardizer, MultiChannelVAD, RTTMWriter

# ── 1. Ses standardizasyonu ──────────────────────────────────────────────────
standardizer = AudioStandardizer()
standardizer.standardize("ham_ses/alice.opus", "islenmis/alice.wav")
standardizer.standardize("ham_ses/bob.opus",   "islenmis/bob.wav")

# ── 2. Standardize edilmiş sesleri numpy dizisine yükle ──────────────────────
alice_audio = standardizer.load_and_standardize("ham_ses/alice.opus")  # float32
bob_audio   = standardizer.load_and_standardize("ham_ses/bob.opus")

# ── 3. Çok kanallı VAD ───────────────────────────────────────────────────────
mcvad = MultiChannelVAD()
segments = mcvad.process({
    "alice": alice_audio,
    "bob":   bob_audio,
})

# segments çıktısı:
# [
#   {"speaker": "alice", "start": 0.0,  "end": 2.3, "type": "single", ...},
#   {"speaker": "overlap", "start": 2.3, "end": 2.9, "type": "overlap",
#    "speakers": ["alice", "bob"]},
#   {"speaker": "bob",   "start": 2.9,  "end": 5.1, "type": "single", ...},
# ]

for seg in segments:
    print(f"[{seg['start']:.2f}s – {seg['end']:.2f}s]  {seg['speaker']}")

# ── 4. RTTM dosyasına kaydet ─────────────────────────────────────────────────
writer = RTTMWriter()
writer.write(segments, "output/toplanti.rttm", recording_id="toplanti_01")

# ── 5. RTTM oku (pyannote uyumlu) ────────────────────────────────────────────
loaded_segments = writer.read("output/toplanti.rttm")
```

---

## Parametre Tablosu

Tüm parametreler `module1_vad/config.py` dosyasında bulunur.

| Parametre | Varsayılan | Açıklama |
|-----------|-----------|----------|
| `SAMPLE_RATE` | `16000` | Hedef örnekleme hızı (Hz). WebRTC ve çoğu ASR sistemiyle uyumlu. |
| `NUM_CHANNELS` | `1` | Çıkış kanalı (1 = mono). |
| `BIT_DEPTH` | `16` | Çıkış bit derinliği (PCM-16). |
| `FRAME_LENGTH_MS` | `25` | Tek analiz çerçevesinin süresi (ms). |
| `HOP_LENGTH_MS` | `10` | Çerçeveler arası atlama (ms). Çakışma = 15 ms. |
| `ADAPTIVE_THRESHOLD_MULTIPLIER` | `1.5` | θ(t) = bu katsayı × son N saniyelik ortalama enerji. |
| `ADAPTIVE_WINDOW_SECONDS` | `10.0` | Adaptif eşik için kullanılan geçmiş pencere (s). |
| `BLEED_RATIO` | `0.15` | Ek(t) < BLEED\_RATIO × max\_j(Ej(t)) → kanal sessiz sayılır. |
| `MIN_SEGMENT_MS` | `300` | Bu sürenin altındaki geçiş segmentleri önceki konuşmacıya atanır. |
| `DEFAULT_RECORDING_ID` | `"meeting"` | RTTM dosyasında kullanılan varsayılan kayıt kimliği. |

---

## Mimariye Genel Bakış

```
ham ses kanalları (WebRTC/OpenVidu)
         │
         ▼
 AudioStandardizer          → 16 kHz mono WAV, peak normalize
         │
         ▼
    EnergyVAD               → Çerçeve bazlı RMS + adaptif eşik
    (kanal başına)
         │
         ▼
 MultiChannelVAD            → Aktivite matrisi + bleed filtreleme
 ├─ Senaryo 1: Tek kanal    → speaker_X (single)
 ├─ Senaryo 2: Çok kanal   → overlap
 └─ Senaryo 3: <300 ms      → önceki konuşmacıya ata
         │
         ▼
   RTTMWriter               → RTTM dosyası (pyannote uyumlu)
```

---

## Testleri Çalıştırma

```bash
# Temel test koşusu
pytest tests/test_module1.py -v

# Kod kapsama raporu ile
pytest tests/test_module1.py -v --cov=module1_vad --cov-report=term-missing

# Tek bir test sınıfı
pytest tests/test_module1.py::TestMultiChannelVAD -v
```

---

## Bilinen Kısıtlamalar

1. **Adaptif eşik başlangıcı**: İlk `ADAPTIVE_WINDOW_SECONDS` saniyede eşik kümülatif ortalamaya dayanır; bu sürede derin sessizlik varsa eşik aşırı düşebilir. Çözüm: ön ısınma verisi eklemek veya minimum bir eşik değeri (`min_floor`) tanımlamak.

2. **Eş uzunluk varsayımı**: `MultiChannelVAD.process()` kanalları en kısa diziye hizalar. Farklı uzunluklu kanallar kırpılır; kırpılan kısım analiz edilmez.

3. **Bellek**: Çok uzun sesler (> 1 saat) için `_frame_audio()` tampon içinde tüm kopyayı bellekte tutar. Gerçek zamanlı kullanım için akış tabanlı (streaming) çerçevelemeye geçilmelidir.

4. **FFmpeg bağımlılığı**: `.opus` dosyaları için PyDub'ın kendi codec desteği sınırlıdır; güvenilir dönüşüm için FFmpeg'in kurulu ve PATH'te erişilebilir olması önerilir.

5. **Overlap çözümü**: Bu modül kimin daha baskın konuştuğunu belirlemez; overlap segmentleri sadece etiketlenir. Baskın konuşmacı ayrıştırması Modül 2 (embedding tabanlı re-scoring) ile yapılacaktır.

6. **Mono varsayımı**: Tüm işlem pipeline'ı mono ses üzerine kuruludur. Stereo girişler mono'ya indirgenir (kanal ortalaması).

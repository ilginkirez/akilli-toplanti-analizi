"""
config.py
---------
Tüm VAD modülü parametrelerini merkezi olarak yönetir.
Hardcode değer kullanmak yerine her sınıf buradan içe aktarır.
"""

# ---------------------------------------------------------------------------
# Ses Standardizasyon Parametreleri
# ---------------------------------------------------------------------------

#: Hedef örnekleme hızı (Hz). WebRTC ve çoğu ASR için standart değer.
SAMPLE_RATE: int = 16000

#: Hedef kanal sayısı (1 = mono).
NUM_CHANNELS: int = 1

#: Çıkış bit derinliği.
BIT_DEPTH: int = 16

#: Desteklenen giriş uzantıları.
#: OpenVidu individual recording çıktıları çoğunlukla .webm gelir.
SUPPORTED_EXTENSIONS: tuple[str, ...] = (
    ".wav",
    ".mp3",
    ".ogg",
    ".opus",
    ".flac",
    ".m4a",
    ".aac",
    ".webm",
)

# ---------------------------------------------------------------------------
# Çerçeveleme Parametreleri
# ---------------------------------------------------------------------------

#: Tek bir analiz çerçevesinin milisaniye cinsinden uzunluğu.
FRAME_LENGTH_MS: int = 25

#: Çerçeveler arası atlama miktarı (ms). Çakışma = FRAME_LENGTH_MS - HOP_LENGTH_MS.
HOP_LENGTH_MS: int = 10

# ---------------------------------------------------------------------------
# Adaptif Eşik Parametreleri
# ---------------------------------------------------------------------------

#: Adaptif eşik çarpanı: θ(t) = ADAPTIVE_THRESHOLD_MULTIPLIER × min-stats.
ADAPTIVE_THRESHOLD_MULTIPLIER: float = 2.5

#: Adaptif eşiği hesaplamak için kullanılan geçmişin süresi (saniye).
ADAPTIVE_WINDOW_SECONDS: float = 30.0

# ---------------------------------------------------------------------------
# Gürültü Tabanı Parametreleri
# ---------------------------------------------------------------------------

#: Per-kanal eşiğin asla düşemeyeceği minimum değer.
#: v2: 1e-4 → 0.01 → 0.02  
#: IHM headset ortam gürültüsü (RMS ~0.01-0.03) yukarıda olduğundan 0.02
#: biraz sessiz konuşmayı kaçırsa da gereksiz kanalları susturur.
NOISE_FLOOR: float = 0.02

#: v3: Global aktivite kapısı.
#: Tüm kanalların en yüksek enerjisi bu değerin altındaysa → gerçek sessizlik,
#: hiçbir kanal aktif sayılmaz. Suskunluk dönemindeki yanlış konuşmacı
#: atamalarını (Confusion) engeller.
#: IHM headset ambient noise max RMS ~0.015-0.025, speech > 0.05.
GLOBAL_SPEECH_FLOOR: float = 0.03

# ---------------------------------------------------------------------------
# Spectral VAD Parametreleri (v2)
# ---------------------------------------------------------------------------

#: Spectral Flatness Measure eşiği.
#: SFM < bu değer → harmonik (konuşma), SFM ≥ bu değer → düz spektrum (gürültü).
SPECTRAL_FLATNESS_THRESHOLD: float = 0.6

# ---------------------------------------------------------------------------
# Cross-Channel Bleed (Kanal Sızıntısı) Parametreleri
# ---------------------------------------------------------------------------

#: Ek(t) < BLEED_RATIO × max_j(Ej(t)) → kanal sessiz sayılır.
#: v2: 0.25 → 0.15 — IHM sızıntısını daha agresif bastırır.
BLEED_RATIO: float = 0.15

# ---------------------------------------------------------------------------
# Dominant Channel Parametreleri (v2)
# ---------------------------------------------------------------------------

#: max_energy / second_max > DOMINANT_RATIO → sadece dominant kanal aktif.
#: v3: 3.0 → 5.0. 3.0 çok agresifti (67 segment/toplantı → çok kaba).
#: 5.0 gerçek bleed'i bastırırken gerçek overlap'leri korur.
DOMINANT_RATIO: float = 5.0

# ---------------------------------------------------------------------------
# IHM Modu Parametreleri
# ---------------------------------------------------------------------------

#: IHM modunda overlap tespiti için minimum enerji oranı eşiği.
#: İki kanal aynı anda aktif göründüğünde:
#:   ikinci_enerji >= IHM_OVERLAP_RATIO × max_enerji → gerçek overlap
#:   ikinci_enerji <  IHM_OVERLAP_RATIO × max_enerji → bleed (bastır)
#: Değer aralığı önerisi: 0.20 – 0.40
#:   0.20: daha fazla overlap kabul eder (FA riski artar)
#:   0.40: daha az overlap kabul eder (Miss riski artar)
IHM_OVERLAP_RATIO: float = 0.30

# ---------------------------------------------------------------------------
# Segment Filtreleme Parametreleri
# ---------------------------------------------------------------------------

#: Bu süreden kısa aktivite segmentleri silinir (ms).
#: v3: 500 → 200. 500ms çok fazla kısa geçişi yutuyordu (1606→67 segment).
MIN_SEGMENT_MS: int = 200

# ---------------------------------------------------------------------------
# RTTM Parametreleri
# ---------------------------------------------------------------------------

#: RTTM yazmak için varsayılan kayıt kimliği.
DEFAULT_RECORDING_ID: str = "meeting"

# ---------------------------------------------------------------------------
# Loglama
# ---------------------------------------------------------------------------

#: Uygulama genelinde kullanılan logger adı.
LOGGER_NAME: str = "meeting_analyzer.vad"

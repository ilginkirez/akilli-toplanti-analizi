"""
config.py
---------
Tum VAD modulu parametrelerini merkezi olarak yonetir.
Hardcode deger kullanmak yerine her sinif buradan ice aktarir.
"""

# ---------------------------------------------------------------------------
# Ses Standardizasyon Parametreleri
# ---------------------------------------------------------------------------

#: Hedef ornekleme hizi (Hz). WebRTC ve cogu ASR icin standart deger.
SAMPLE_RATE: int = 16000

#: Hedef kanal sayisi (1 = mono).
NUM_CHANNELS: int = 1

#: Cikis bit derinligi.
BIT_DEPTH: int = 16

#: Desteklenen giris uzantilari.
#: Tarayici tabanli bireysel kayit ciktilari cogunlukla .webm gelir.
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
# Cerceveleme Parametreleri
# ---------------------------------------------------------------------------

#: Tek bir analiz cercevesinin milisaniye cinsinden uzunlugu.
FRAME_LENGTH_MS: int = 25

#: Cerceveler arasi atlama miktari (ms). Cakisma = FRAME_LENGTH_MS - HOP_LENGTH_MS.
HOP_LENGTH_MS: int = 10

# ---------------------------------------------------------------------------
# Adaptif Esik Parametreleri
# ---------------------------------------------------------------------------

#: Adaptif esik carpani: theta(t) = ADAPTIVE_THRESHOLD_MULTIPLIER x min-stats.
ADAPTIVE_THRESHOLD_MULTIPLIER: float = 2.5

#: Adaptif esigi hesaplamak icin kullanilan gecmisin suresi (saniye).
ADAPTIVE_WINDOW_SECONDS: float = 30.0

# ---------------------------------------------------------------------------
# Gurultu Tabani Parametreleri
# ---------------------------------------------------------------------------

#: Per-kanal esigin asla dusemeyecegi minimum deger.
#: v2: 1e-4 -> 0.01 -> 0.02
#: IHM headset ortam gurultusu (RMS ~0.01-0.03) yukarida oldugundan 0.02
#: biraz sessiz konusmayi kacirsa da gereksiz kanallari susturur.
NOISE_FLOOR: float = 0.02

#: v3: Global aktivite kapisi.
#: Tum kanallarin en yuksek enerjisi bu degerin altindaysa -> gercek sessizlik,
#: hicbir kanal aktif sayilmaz. Suskunluk donemindeki yanlis konusmaci
#: atamalarini (Confusion) engeller.
#: IHM headset ambient noise max RMS ~0.015-0.025, speech > 0.05.
GLOBAL_SPEECH_FLOOR: float = 0.03

# ---------------------------------------------------------------------------
# Spectral VAD Parametreleri (v2)
# ---------------------------------------------------------------------------

#: Spectral Flatness Measure esigi.
#: SFM < bu deger -> harmonik (konusma), SFM >= bu deger -> duz spektrum (gurultu).
SPECTRAL_FLATNESS_THRESHOLD: float = 0.6

# ---------------------------------------------------------------------------
# Cross-Channel Bleed (Kanal Sizintisi) Parametreleri
# ---------------------------------------------------------------------------

#: Ek(t) < BLEED_RATIO x max_j(Ej(t)) -> kanal sessiz sayilir.
#: v2: 0.25 -> 0.15 - IHM sizintisini daha agresif bastirir.
BLEED_RATIO: float = 0.15

# ---------------------------------------------------------------------------
# Dominant Channel Parametreleri (v2)
# ---------------------------------------------------------------------------

#: max_energy / second_max > DOMINANT_RATIO -> sadece dominant kanal aktif.
#: v3: 3.0 -> 5.0. 3.0 cok agresifti (67 segment/toplanti -> cok kaba).
#: 5.0 gercek bleed'i bastirirken gercek overlap'leri korur.
DOMINANT_RATIO: float = 5.0

# ---------------------------------------------------------------------------
# IHM Modu Parametreleri
# ---------------------------------------------------------------------------

#: IHM modunda overlap tespiti icin minimum enerji orani esigi.
#: Iki kanal ayni anda aktif gorundugunde:
#:   ikinci_enerji >= IHM_OVERLAP_RATIO x max_enerji -> gercek overlap
#:   ikinci_enerji <  IHM_OVERLAP_RATIO x max_enerji -> bleed (bastir)
#: Deger araligi onerisi: 0.20 - 0.40
#:   0.20: daha fazla overlap kabul eder (FA riski artar)
#:   0.40: daha az overlap kabul eder (Miss riski artar)
IHM_OVERLAP_RATIO: float = 0.30

# ---------------------------------------------------------------------------
# Segment Filtreleme Parametreleri
# ---------------------------------------------------------------------------

#: Bu sureden kisa aktivite segmentleri silinir (ms).
#: v3: 500 -> 200. 500ms cok fazla kisa gecisi yutuyordu (1606->67 segment).
MIN_SEGMENT_MS: int = 200

# ---------------------------------------------------------------------------
# RTTM Parametreleri
# ---------------------------------------------------------------------------

#: RTTM yazmak icin varsayilan kayit kimligi.
DEFAULT_RECORDING_ID: str = "meeting"

# ---------------------------------------------------------------------------
# Loglama
# ---------------------------------------------------------------------------

#: Uygulama genelinde kullanilan logger adi.
LOGGER_NAME: str = "meeting_analyzer.vad"

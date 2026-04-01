"""
energy_vad.py
-------------
Adaptif eşik tabanlı Enerji VAD (Voice Activity Detection) sınıfı.

Algoritma:
    1. Ses sinyali çerçevelere bölünür (kayan pencere).
    2. Her çerçeve için RMS enerji hesaplanır.
    3. Adaptif eşik: θ(t) = ADAPTIVE_THRESHOLD_MULTIPLIER × (son N saniyedeki ortalama enerji)
    4. v2: Spectral Flatness Measure (SFM) eklendi.
       aktif = (RMS > θ) AND (SFM < SPECTRAL_FLATNESS_THRESHOLD)
       Gürültü düz spektruma sahipken konuşma harmoniktir (SFM düşük).
"""

import logging
from dataclasses import dataclass

import numpy as np
from scipy import signal as scipy_signal

from . import config

logger = logging.getLogger(config.LOGGER_NAME)


@dataclass
class VADResult:
    """
    Tek bir kanalın VAD analiz sonucunu taşıyan veri sınıfı.

    Attributes:
        frame_activity : (T,) bool dizisi – her çerçeve için aktif mi?
        frame_energies : (T,) float32 dizisi – ham RMS enerji değerleri.
        thresholds     : (T,) float32 dizisi – her çerçeve için adaptif eşik.
        frame_times    : (T,) float64 dizisi – çerçevelerin başlangıç zamanı (s).
        spectral_flatness : (T,) float32 dizisi – her çerçeve için SFM değeri (v2).
    """
    frame_activity: np.ndarray   # bool
    frame_energies: np.ndarray   # float32
    thresholds: np.ndarray       # float32
    frame_times: np.ndarray      # float64
    spectral_flatness: np.ndarray = None  # float32, v2: None ise spectral kapalı


class EnergyVAD:
    """
    Adaptif enerji eşiği kullanan Voice Activity Detector.

    Her çerçeve için RMS enerji hesaplar ve dinamik olarak güncellenen
    bir eşikle karşılaştırır. Cross-channel bleed tespiti için ham enerji
    değerlerini de saklar.

    v2: Spectral Flatness Measure (SFM) eklendi. use_spectral=True iken
    konuşma kararı hem enerji hem de spektral düzlük kriterine bağlıdır.

    Attributes:
        sample_rate          (int)   : Beklenen örnekleme hızı.
        frame_length_ms      (int)   : Çerçeve uzunluğu (ms).
        hop_length_ms        (int)   : Çerçeve atlama miktarı (ms).
        threshold_multiplier (float) : Adaptif eşik çarpanı.
        adaptive_window_sec  (float) : Adaptif pencere genişliği (s).
        use_spectral         (bool)  : v2: SFM filtresi açık mı?
        sfm_threshold        (float) : v2: SFM eşik değeri.
    """

    def __init__(
        self,
        sample_rate: int = config.SAMPLE_RATE,
        frame_length_ms: int = config.FRAME_LENGTH_MS,
        hop_length_ms: int = config.HOP_LENGTH_MS,
        threshold_multiplier: float = config.ADAPTIVE_THRESHOLD_MULTIPLIER,
        adaptive_window_sec: float = config.ADAPTIVE_WINDOW_SECONDS,
        noise_floor: float = config.NOISE_FLOOR,
        use_spectral: bool = True,
        sfm_threshold: float = config.SPECTRAL_FLATNESS_THRESHOLD,
    ) -> None:
        """
        EnergyVAD örneği oluşturur.

        Args:
            sample_rate          : Ses örnekleme hızı (Hz).
            frame_length_ms      : Analiz çerçevesinin uzunluğu (ms).
            hop_length_ms        : Çerçeveler arası atlama (ms).
            threshold_multiplier : θ = multiplier × ortalama geçmiş enerji.
            adaptive_window_sec  : Eşik hesabında kullanılan geçmiş pencere (s).
            noise_floor          : Eşiğin asla düşemeyeceği minimum değer.
                                   v2: 1e-4 → 0.01 (config.NOISE_FLOOR).
            use_spectral         : v2: True ise SFM filtresi aktif, False ise
                                   eski RMS-only davranışı (geriye uyumluluk).
            sfm_threshold        : v2: SFM eşiği. SFM < bu değer → konuşma.
        """
        self.sample_rate = sample_rate
        self.frame_length_ms = frame_length_ms
        self.hop_length_ms = hop_length_ms
        self.threshold_multiplier = threshold_multiplier
        self.adaptive_window_sec = adaptive_window_sec
        self.noise_floor = noise_floor
        # v2: spectral flatness parametreleri
        self.use_spectral = use_spectral
        self.sfm_threshold = sfm_threshold

        # Örnek cinsinden hesaplanan sabitler
        self._frame_length_samples: int = int(sample_rate * frame_length_ms / 1000)
        self._hop_length_samples: int = int(sample_rate * hop_length_ms / 1000)
        self._adaptive_window_frames: int = int(
            adaptive_window_sec * 1000 / hop_length_ms
        )

        logger.debug(
            "EnergyVAD başlatıldı: frame=%d smp, hop=%d smp, adapt_win=%d frames, "
            "floor=%.2e, spectral=%s, sfm_thresh=%.2f",
            self._frame_length_samples,
            self._hop_length_samples,
            self._adaptive_window_frames,
            noise_floor,
            use_spectral,
            sfm_threshold,
        )

    # ------------------------------------------------------------------
    # Genel API
    # ------------------------------------------------------------------

    def detect(self, audio: np.ndarray, sample_rate: int) -> VADResult:
        """
        Ses dizisini analiz eder ve çerçeve bazlı VAD sonuçları üretir.

        # v2: Spectral Flatness Measure eklendi.
        # Eski davranış: aktif = RMS > θ
        # Yeni davranış: aktif = (RMS > θ) AND (SFM < sfm_threshold)
        # use_spectral=False ile eski davranışa dönülebilir.

        Args:
            audio       : float32 numpy dizisi, şekil (N,).
            sample_rate : Dizinin örnekleme hızı.

        Returns:
            VADResult: Aktivite dizisi, ham enerjiler, eşikler, zaman damgaları
                       ve spectral_flatness (v2).

        Raises:
            ValueError : Ses boşsa veya örnekleme hızı eşleşmiyorsa.
        """
        audio = self._validate_audio(audio, sample_rate)

        # Çerçeveleme ve RMS enerji hesabi
        frames = self._frame_audio(audio)                          # (T, L)
        energies = self._rms(frames)                               # (T,) float32

        # Adaptif eşik ve enerji kararı
        thresholds = self._adaptive_threshold(energies)            # (T,) float32
        energy_active = energies > thresholds                      # (T,) bool

        # v2: Spectral Flatness filtresi
        sfm_values = None
        if self.use_spectral:
            sfm_values = self._spectral_flatness(frames)           # (T,) float32
            spectral_active = sfm_values < self.sfm_threshold      # (T,) bool
            activity = energy_active & spectral_active             # (T,) bool
        else:
            activity = energy_active

        # Çerçeve başlangıç zamanları (saniye)
        frame_times = (
            np.arange(len(energies)) * self._hop_length_samples / self.sample_rate
        ).astype(np.float64)

        logger.debug(
            "VAD tamamlandı: %d çerçeveden %d aktif (%.1f%%)%s",
            len(activity),
            activity.sum(),
            100 * activity.mean(),
            " [spectral ON]" if self.use_spectral else "",
        )

        return VADResult(
            frame_activity=activity,
            frame_energies=energies,
            thresholds=thresholds,
            frame_times=frame_times,
            spectral_flatness=sfm_values,
        )

    def frames_to_seconds(self, frame_index: int) -> float:
        """
        Çerçeve indeksini saniyeye dönüştürür.

        Args:
            frame_index : Çerçeve dizini (sıfır tabanlı).

        Returns:
            Çerçevenin merkezi saniye cinsinden.
        """
        return frame_index * self._hop_length_samples / self.sample_rate

    def seconds_to_frame(self, seconds: float) -> int:
        """
        Saniyeyi en yakın çerçeve indeksine dönüştürür.

        Args:
            seconds : Zaman (s).

        Returns:
            En yakın çerçeve indeksi.
        """
        return int(round(seconds * self.sample_rate / self._hop_length_samples))

    # ------------------------------------------------------------------
    # Dahili metodlar
    # ------------------------------------------------------------------

    def _validate_audio(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Ses dizisini doğrular ve float32'ye dönüştürür."""
        if audio is None or len(audio) == 0:
            raise ValueError("Ses dizisi boş olamaz.")
        if sample_rate != self.sample_rate:
            raise ValueError(
                f"Örnekleme hızı uyuşmazlığı: beklenen {self.sample_rate}, "
                f"gelen {sample_rate}. Önce AudioStandardizer kullanın."
            )
        return audio.astype(np.float32)

    def _frame_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Sesi örtüşen çerçevelere böler.

        scipy.signal.stft yerine daha kontrollü bir pencere oluşturma kullanır.

        Args:
            audio : float32 (N,)

        Returns:
            float32 (T, frame_length_samples)
        """
        n_samples = len(audio)
        frame_len = self._frame_length_samples
        hop_len = self._hop_length_samples

        # Çerçeve sayısı
        if n_samples < frame_len:
            # Çok kısa ses – sıfırla doldur
            padded = np.zeros(frame_len, dtype=np.float32)
            padded[:n_samples] = audio
            return padded[np.newaxis, :]

        # scipy striding trick ile verimli çerçeveleme
        num_frames = 1 + (n_samples - frame_len) // hop_len
        shape = (num_frames, frame_len)
        strides = (hop_len * audio.itemsize, audio.itemsize)
        frames = np.lib.stride_tricks.as_strided(audio, shape=shape, strides=strides)
        return np.array(frames, dtype=np.float32)  # kopya – salt okunur hatası yok

    @staticmethod
    def _rms(frames: np.ndarray) -> np.ndarray:
        """
        Her çerçeve için Root Mean Square enerji hesaplar.

        Args:
            frames : float32 (T, L)

        Returns:
            float32 (T,)
        """
        return np.sqrt(np.mean(frames ** 2, axis=1)).astype(np.float32)

    def _adaptive_threshold(self, energies: np.ndarray) -> np.ndarray:
        """
        Her çerçeve için minimum istatistik tabanlı adaptif enerji eşiği hesaplar.

        Algoritma:
            - Kayan penceredeki **minimum** enerjiyi izler → gürültü tahmini.
            - θ(t) = max(MULTIPLIER x min(energies[t-W : t+1]), noise_floor)
            - ``mean``-tabanlı yaklaşımdan farkı: sürekli konuşan bir kanalda
              ortalama enerji yüksek olur ve eşik de yükselir; minimum ise
              arka plan gürültü tabannı yakalar.
            - Sessiz ortamlarda noise_floor güvence altı sağlar.

        Args:
            energies : float32 (T,) – RMS enerji değerleri.

        Returns:
            float32 (T,) – her çerçeve için θ değeri.
        """
        n_frames = len(energies)
        W = max(1, self._adaptive_window_frames)
        thresholds = np.empty(n_frames, dtype=np.float32)

        # Global %10 percentile: sinyalin en sessiz (arka plan) bolgesini temsil eder.
        global_min = float(np.percentile(energies, 10))

        for t in range(n_frames):
            start = max(0, t - W)
            local_min = float(energies[start : t + 1].min())
            # Noise estimate: yerel ve global minimumu karistir
            noise_estimate = 0.7 * local_min + 0.3 * global_min
            thresholds[t] = max(
                self.threshold_multiplier * noise_estimate,
                self.noise_floor,
            )

        return thresholds.astype(np.float32)

    # v2: Spectral Flatness Measure hesaplayan yeni metod
    @staticmethod
    def _spectral_flatness(frames: np.ndarray) -> np.ndarray:
        """
        Her çerçeve için Spectral Flatness Measure (SFM) hesaplar.

        SFM = geometric_mean(|X(k)|) / arithmetic_mean(|X(k)|)

        Konuşma harmonik yapıda olduğundan SFM düşüktür (~0.1-0.4).
        Beyaz gürültü düz spektruma sahip olduğundan SFM yüksektir (~1.0).

        Args:
            frames : float32 (T, L)

        Returns:
            float32 (T,) – her çerçeve için SFM değeri [0, 1].
        """
        # FFT al — sadece pozitif frekansları kullan
        n_fft = frames.shape[1]
        spectrum = np.abs(np.fft.rfft(frames, n=n_fft, axis=1))  # (T, n_fft//2+1)

        # DC bileşenini atla (index 0), çok küçük değerleri clamp et
        spectrum = spectrum[:, 1:]  # DC hariç
        eps = 1e-10
        spectrum = np.maximum(spectrum, eps)

        # Geometrik ortalama: exp(mean(log(x))) — numerik kararlılık
        log_spectrum = np.log(spectrum)
        geo_mean = np.exp(np.mean(log_spectrum, axis=1))

        # Aritmetik ortalama
        arith_mean = np.mean(spectrum, axis=1)

        # SFM = geo / arith, [0, 1] aralığına sıkıştır
        sfm = np.clip(geo_mean / (arith_mean + eps), 0.0, 1.0)

        return sfm.astype(np.float32)

    # ------------------------------------------------------------------
    # Özellik sorgulama
    # ------------------------------------------------------------------

    @property
    def frame_duration(self) -> float:
        """Bir çerçevenin saniye cinsinden süresi."""
        return self._frame_length_samples / self.sample_rate

    @property
    def hop_duration(self) -> float:
        """Çerçeveler arası atlama süresi (s)."""
        return self._hop_length_samples / self.sample_rate

"""
audio_standardizer.py
---------------------
Ham ses dosyalarını 16 kHz mono WAV formatına dönüştürür ve
genlik normalizasyonu uygular.

Desteklenen giriş formatları: .wav, .mp3, .ogg, .opus, .flac, .m4a, .aac
"""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import numpy as np

from . import config

logger = logging.getLogger(config.LOGGER_NAME)


class AudioStandardizationError(Exception):
    """Ses standardizasyonu sırasında oluşan hatalar için özel exception."""
    pass


class AudioStandardizer:
    """
    Ham ses dosyalarını sisteme uygun standart formata dönüştüren sınıf.

    Standart format:
        - Örnekleme hızı : 16 000 Hz
        - Kanal          : Mono (1)
        - Bit derinliği  : 16-bit PCM
        - Genlik         : Peak normalizasyon [-1.0, 1.0]

    Öncelik sırası:
        1. FFmpeg (yüklü ise) – en güvenilir ve hızlı yol.
        2. PyDub               – FFmpeg bulunamazsa fallback.

    Attributes:
        sample_rate  (int)  : Hedef örnekleme hızı.
        num_channels (int)  : Hedef kanal sayısı.
        bit_depth    (int)  : Hedef bit derinliği.
    """

    def __init__(
        self,
        sample_rate: int = config.SAMPLE_RATE,
        num_channels: int = config.NUM_CHANNELS,
        bit_depth: int = config.BIT_DEPTH,
    ) -> None:
        """
        AudioStandardizer örneği oluşturur.

        Args:
            sample_rate  : Çıkış örnekleme hızı (Hz). Varsayılan: 16000.
            num_channels : Çıkış kanal sayısı. Varsayılan: 1 (mono).
            bit_depth    : Çıkış bit derinliği. Varsayılan: 16.
        """
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.bit_depth = bit_depth
        self._ffmpeg_available: Optional[bool] = None

        logger.debug(
            "AudioStandardizer başlatıldı: sr=%d, ch=%d, bit=%d",
            sample_rate, num_channels, bit_depth,
        )

    # ------------------------------------------------------------------
    # Genel API
    # ------------------------------------------------------------------

    def standardize(self, input_path: str | Path, output_path: str | Path) -> Path:
        """
        Ses dosyasını okur, standart formata dönüştürür ve diske yazar.

        Args:
            input_path  : Kaynak ses dosyasının yolu.
            output_path : Hedef WAV dosyasının yolu.

        Returns:
            Çıkış dosyasının mutlak Path nesnesi.

        Raises:
            AudioStandardizationError : Dönüşüm veya normalizasyon başarısız olursa.
            FileNotFoundError          : Kaynak dosya bulunamazsa.
            ValueError                 : Desteklenmeyen dosya uzantısı girilirse.
        """
        input_path = Path(input_path).resolve()
        output_path = Path(output_path).resolve()

        self._validate_input(input_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Standardizasyon başladı: %s → %s", input_path, output_path)

        # 1. Dönüşüm (FFmpeg veya PyDub)
        raw_output = output_path.with_suffix(".raw.wav")
        try:
            if self._is_ffmpeg_available():
                self._convert_with_ffmpeg(input_path, raw_output)
            else:
                self._convert_with_pydub(input_path, raw_output)
        except Exception as exc:
            raise AudioStandardizationError(
                f"Ses dönüşümü başarısız: {input_path} → {exc}"
            ) from exc

        # 2. Genlik normalizasyonu
        try:
            audio_array = self._load_wav_as_float32(raw_output)
            normalized = self._peak_normalize(audio_array)
            self._save_float32_as_wav(normalized, output_path)
        except Exception as exc:
            raise AudioStandardizationError(
                f"Normalizasyon başarısız: {exc}"
            ) from exc
        finally:
            if raw_output.exists():
                raw_output.unlink()

        logger.info("Standardizasyon tamamlandı: %s", output_path)
        return output_path

    def load_and_standardize(self, input_path: str | Path) -> np.ndarray:
        """
        Ses dosyasını okur, standardize eder ve numpy dizisi olarak döndürür.
        Geçici dosya kullanır; disk üzerine kalıcı çıkış yazmaz.

        Args:
            input_path : Kaynak ses dosyasının yolu.

        Returns:
            float32 numpy dizisi, şekil (N,), normalize edilmiş [-1.0, 1.0].

        Raises:
            AudioStandardizationError : İşlem başarısız olursa.
        """
        import tempfile

        input_path = Path(input_path).resolve()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_out = Path(tmpdir) / "standardized.wav"
            self.standardize(input_path, tmp_out)
            return self._load_wav_as_float32(tmp_out)

    # ------------------------------------------------------------------
    # Dahili yardımcı metodlar
    # ------------------------------------------------------------------

    def _validate_input(self, path: Path) -> None:
        """Giriş dosyasını doğrular; hata durumunda exception fırlatır."""
        if not path.exists():
            raise FileNotFoundError(f"Ses dosyası bulunamadı: {path}")
        if path.suffix.lower() not in config.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Desteklenmeyen uzantı '{path.suffix}'. "
                f"Desteklenenler: {config.SUPPORTED_EXTENSIONS}"
            )
        if path.stat().st_size == 0:
            raise AudioStandardizationError(f"Ses dosyası boş: {path}")

    def _is_ffmpeg_available(self) -> bool:
        """FFmpeg'in PATH'te mevcut olup olmadığını önbellekli olarak kontrol eder."""
        if self._ffmpeg_available is None:
            self._ffmpeg_available = shutil.which("ffmpeg") is not None
            if self._ffmpeg_available:
                logger.debug("FFmpeg bulundu, birincil dönüştürücü olarak kullanılacak.")
            else:
                logger.warning("FFmpeg bulunamadı. PyDub fallback'i deneniyor.")
        return self._ffmpeg_available

    def _convert_with_ffmpeg(self, input_path: Path, output_path: Path) -> None:
        """
        FFmpeg subprocess kullanarak formatı dönüştürür.

        Args:
            input_path  : Kaynak dosya.
            output_path : Hedef WAV dosyası (ham, normalize edilmemiş).

        Raises:
            AudioStandardizationError : FFmpeg sıfır olmayan çıkış kodu döndürürse.
        """
        cmd = [
            "ffmpeg",
            "-y",                          # Üzerine yaz
            "-i", str(input_path),
            "-ar", str(self.sample_rate),  # Örnekleme hızı
            "-ac", str(self.num_channels), # Kanal sayısı
            "-sample_fmt", "s16",          # 16-bit PCM
            str(output_path),
        ]
        logger.debug("FFmpeg komutu: %s", " ".join(cmd))

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AudioStandardizationError(
                f"FFmpeg hatası (kod {result.returncode}):\n{result.stderr}"
            )

    def _convert_with_pydub(self, input_path: Path, output_path: Path) -> None:
        """
        PyDub kullanarak formatı dönüştürür (FFmpeg fallback).

        Args:
            input_path  : Kaynak dosya.
            output_path : Hedef WAV dosyası.

        Raises:
            AudioStandardizationError : PyDub yüklü değilse veya dönüşüm başarısızsa.
        """
        try:
            from pydub import AudioSegment
        except ImportError as exc:
            raise AudioStandardizationError(
                "PyDub yüklü değil ve FFmpeg bulunamadı. "
                "Lütfen 'pip install pydub' veya FFmpeg yükleyin."
            ) from exc

        fmt = input_path.suffix.lstrip(".")
        if fmt == "opus":
            fmt = "ogg"  # PyDub .opus'u ogg codec olarak işler

        logger.debug("PyDub ile dönüşüm: format=%s", fmt)
        audio = AudioSegment.from_file(str(input_path), format=fmt)
        audio = audio.set_frame_rate(self.sample_rate)
        audio = audio.set_channels(self.num_channels)
        audio = audio.set_sample_width(self.bit_depth // 8)
        audio.export(str(output_path), format="wav")

    @staticmethod
    def _load_wav_as_float32(wav_path: Path) -> np.ndarray:
        """
        WAV dosyasını float32 numpy dizisi olarak okur.

        Args:
            wav_path : WAV dosyasının yolu.

        Returns:
            float32 dizisi (N,). Stereo ise mono'ya dönüştürür.

        Raises:
            AudioStandardizationError : Dosya okunamazsa.
        """
        try:
            import soundfile as sf
            data, _ = sf.read(str(wav_path), dtype="float32", always_2d=False)
        except Exception:
            try:
                import scipy.io.wavfile as wavfile
                sr, data = wavfile.read(str(wav_path))
                data = data.astype(np.float32)
                # 16-bit int → float32 normalize
                if data.dtype != np.float32:
                    data = data / np.iinfo(np.int16).max
            except Exception as exc:
                raise AudioStandardizationError(
                    f"WAV dosyası okunamadı: {wav_path} → {exc}"
                ) from exc

        # Stereo → mono
        if data.ndim == 2:
            data = data.mean(axis=1)

        return data.astype(np.float32)

    @staticmethod
    def _peak_normalize(audio: np.ndarray) -> np.ndarray:
        """
        Peak normalizasyonu uygular: en yüksek genliği 1.0'a ölçekler.

        Sessiz ses (tüm değerler 0) için orijinal diziyi değiştirmeden döndürür.

        Args:
            audio : float32 numpy dizisi.

        Returns:
            Normalize edilmiş float32 dizisi, aralık [-1.0, 1.0].
        """
        peak = np.max(np.abs(audio))
        if peak < 1e-9:
            logger.warning("Ses tamamen sessiz görünüyor, normalizasyon atlandı.")
            return audio
        return (audio / peak).astype(np.float32)

    @staticmethod
    def _save_float32_as_wav(audio: np.ndarray, output_path: Path) -> None:
        """
        float32 numpy dizisini 16-bit PCM WAV olarak diske yazar.

        Args:
            audio       : float32 numpy dizisi, aralık [-1.0, 1.0].
            output_path : Hedef WAV dosyası yolu.

        Raises:
            AudioStandardizationError : Yazma başarısız olursa.
        """
        try:
            import soundfile as sf
            sf.write(str(output_path), audio, config.SAMPLE_RATE, subtype="PCM_16")
        except Exception:
            try:
                import scipy.io.wavfile as wavfile
                pcm16 = (audio * np.iinfo(np.int16).max).astype(np.int16)
                wavfile.write(str(output_path), config.SAMPLE_RATE, pcm16)
            except Exception as exc:
                raise AudioStandardizationError(
                    f"WAV dosyası yazılamadı: {output_path} → {exc}"
                ) from exc

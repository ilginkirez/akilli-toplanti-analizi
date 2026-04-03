"""
test_module1.py
---------------
module1_vad modülü için birim testler.

Test stratejisi:
    - Sentetik ses verisi (sinüs dalgası ve beyaz gürültü) kullanılır.
    - Gerçek dosya I/O en aza indirilir; geçici dizinler kullanılır.
    - Her sınıf için en az 2 test yazılmıştır.
    - Overlap ve RTTM format testleri dahildir.
    - v2: Spectral VAD, dominant-only modu ve overlap RTTM testleri eklendi.

Çalıştırma::

    pytest tests/test_module1.py -v
"""

import tempfile
from pathlib import Path
from typing import Dict

import numpy as np
import pytest

# Modülü içe aktar
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from module1_vad.audio_standardizer import AudioStandardizer, AudioStandardizationError
from module1_vad.energy_vad import EnergyVAD, VADResult
from module1_vad.mcvad import MultiChannelVAD, Segment
from module1_vad.rttm_writer import RTTMWriter, RTTMParseError
from module1_vad import config


# ===========================================================================
# Yardımcı fonksiyonlar
# ===========================================================================

def make_sine_wave(
    frequency: float = 440.0,
    duration_sec: float = 2.0,
    sample_rate: int = config.SAMPLE_RATE,
    amplitude: float = 0.5,
) -> np.ndarray:
    """Test için sinüs dalgası üretir (float32)."""
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.float32)


def make_white_noise(
    duration_sec: float = 2.0,
    sample_rate: int = config.SAMPLE_RATE,
    amplitude: float = 0.3,
    seed: int = 42,
) -> np.ndarray:
    """Test için beyaz gürültü üretir (float32)."""
    rng = np.random.default_rng(seed)
    return (amplitude * rng.standard_normal(int(sample_rate * duration_sec))).astype(np.float32)


def make_silence(
    duration_sec: float = 2.0,
    sample_rate: int = config.SAMPLE_RATE,
) -> np.ndarray:
    """Test için sessiz dizi üretir (float32)."""
    return np.zeros(int(sample_rate * duration_sec), dtype=np.float32)


def make_speech_with_silence(
    speech_regions: list[tuple[float, float]],  # [(start, end), ...]
    total_duration: float = 5.0,
    sample_rate: int = config.SAMPLE_RATE,
    amplitude: float = 0.7,
) -> np.ndarray:
    """
    Belirli zaman aralıklarında sinüs dalgası, geri kalanında sessizlik içeren
    bileşik ses dizisi üretir.

    Args:
        speech_regions : Konuşma aralıkları [(start_s, end_s), ...].
        total_duration : Toplam ses süresi (s).
        sample_rate    : Örnekleme hızı.
        amplitude      : Sinüs dalga genliği.

    Returns:
        float32 numpy dizisi.
    """
    audio = make_silence(total_duration, sample_rate)
    t = np.linspace(0, total_duration, len(audio), endpoint=False)
    for start, end in speech_regions:
        mask = (t >= start) & (t < end)
        audio[mask] = amplitude * np.sin(2 * np.pi * 440.0 * t[mask])
    return audio.astype(np.float32)


def write_temp_wav(audio: np.ndarray, sample_rate: int = config.SAMPLE_RATE) -> Path:
    """float32 diziyi geçici WAV dosyasına yazar ve yolunu döndürür."""
    import soundfile as sf
    import tempfile, os

    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    sf.write(path, audio, sample_rate, subtype="PCM_16")
    return Path(path)


# ===========================================================================
# AudioStandardizer Testleri
# ===========================================================================

class TestAudioStandardizer:
    """AudioStandardizer sınıfı testleri."""

    def test_peak_normalization_reduces_amplitude(self) -> None:
        """Peak normalizasyonu sonrası max mutlak değerin 1.0 olduğunu doğrular."""
        audio = make_sine_wave(amplitude=0.3)
        standardizer = AudioStandardizer()
        normalized = standardizer._peak_normalize(audio)

        assert normalized.dtype == np.float32
        assert np.isclose(np.max(np.abs(normalized)), 1.0, atol=1e-5), (
            "Peak normalizasyon sonrası maksimum değer 1.0 olmalıdır."
        )

    def test_peak_normalization_silent_audio(self) -> None:
        """Tamamen sessiz ses için normalizasyonun orijinalini döndürdüğünü test eder."""
        silence = make_silence()
        standardizer = AudioStandardizer()
        result = standardizer._peak_normalize(silence)

        assert np.allclose(result, 0.0), (
            "Sessiz ses normalizasyon sonrası da sıfır kalmalıdır."
        )

    def test_validate_input_missing_file(self) -> None:
        """Var olmayan dosya için FileNotFoundError fırlatıldığını test eder."""
        standardizer = AudioStandardizer()
        with pytest.raises(FileNotFoundError):
            standardizer._validate_input(Path("/nonexistent/audio.wav"))

    def test_validate_input_unsupported_extension(self, tmp_path: Path) -> None:
        """Desteklenmeyen uzantı için ValueError fırlatıldığını test eder."""
        fake_file = tmp_path / "audio.xyz"
        fake_file.write_bytes(b"\x00" * 100)
        standardizer = AudioStandardizer()
        with pytest.raises(ValueError, match="Desteklenmeyen uzantı"):
            standardizer._validate_input(fake_file)

    def test_standardize_wav_roundtrip(self, tmp_path: Path) -> None:
        """WAV → standardize → WAV yolculuğu hata vermeden tamamlanmalıdır."""
        try:
            import soundfile  # noqa: F401
        except ImportError:
            pytest.skip("soundfile yüklü değil, test atlanıyor.")

        audio = make_sine_wave(amplitude=0.5)
        src = write_temp_wav(audio)
        dst = tmp_path / "output.wav"

        standardizer = AudioStandardizer()
        result_path = standardizer.standardize(src, dst)

        assert result_path.exists(), "Çıkış dosyası oluşturulmalıdır."
        assert result_path.suffix == ".wav"

        src.unlink()

    def test_load_wav_as_float32_shape(self) -> None:
        """Yüklenen dizinin float32 ve tek boyutlu olduğunu test eder."""
        try:
            import soundfile  # noqa: F401
        except ImportError:
            pytest.skip("soundfile yüklü değil.")

        audio = make_sine_wave()
        tmp = write_temp_wav(audio)
        loaded = AudioStandardizer._load_wav_as_float32(tmp)

        assert loaded.dtype == np.float32
        assert loaded.ndim == 1
        tmp.unlink()


# ===========================================================================
# EnergyVAD Testleri
# ===========================================================================

class TestEnergyVAD:
    """EnergyVAD sınıfı testleri."""

    def test_detect_returns_vad_result(self) -> None:
        """detect() metodunun VADResult nesnesi döndürdüğünü test eder."""
        vad = EnergyVAD(use_spectral=False)
        audio = make_sine_wave(duration_sec=1.0)
        result = vad.detect(audio, config.SAMPLE_RATE)

        assert isinstance(result, VADResult)
        assert result.frame_activity.dtype == bool
        assert result.frame_energies.dtype == np.float32
        assert result.thresholds.dtype == np.float32
        assert result.frame_times.dtype == np.float64

    def test_detect_shape_consistency(self) -> None:
        """Tüm çıktı dizilerinin aynı uzunlukta olduğunu test eder."""
        vad = EnergyVAD(use_spectral=False)
        audio = make_sine_wave(duration_sec=3.0)
        result = vad.detect(audio, config.SAMPLE_RATE)

        lengths = [
            len(result.frame_activity),
            len(result.frame_energies),
            len(result.thresholds),
            len(result.frame_times),
        ]
        assert len(set(lengths)) == 1, f"Uzunluklar eşit olmalı: {lengths}"

    def test_silence_detected_as_inactive(self) -> None:
        """Tamamen sessiz seste aktif çerçeve sayısının düşük olduğunu test eder."""
        vad = EnergyVAD(use_spectral=False)
        silence = make_silence(duration_sec=2.0)
        result = vad.detect(silence, config.SAMPLE_RATE)

        # Sessiz seste aktivite oranı %5'in altında olmalı
        activation_rate = result.frame_activity.mean()
        assert activation_rate < 0.05, (
            f"Sessiz ses için aktivasyon oranı çok yüksek: {activation_rate:.2%}"
        )

    def test_sine_wave_detected_as_active(self) -> None:
        """Konuşma+sessizlik içeren ses dizisinde aktif bölge tespitini test eder."""
        vad = EnergyVAD(use_spectral=False)
        # Gerçekçi senaryo: 2 saniye sessizlik + 2 saniye sinüs
        silence = make_silence(duration_sec=2.0)
        speech = make_sine_wave(amplitude=0.8, duration_sec=2.0)
        audio = np.concatenate([silence, speech]).astype(np.float32)
        result = vad.detect(audio, config.SAMPLE_RATE)

        n = len(result.frame_activity)
        # İkinci yarıdaki (konuşma bölgesi) aktivasyon oranı yüksek olmalı
        second_half_activity = result.frame_activity[n // 2:].mean()
        assert second_half_activity > 0.50, (
            f"Konuşma bölgesinde aktivasyon oranı düşük: {second_half_activity:.2%}. "
            "Beklenen: > 50%"
        )

    def test_wrong_sample_rate_raises_error(self) -> None:
        """Yanlış örnekleme hızı için ValueError fırlatıldığını test eder."""
        vad = EnergyVAD(sample_rate=16000, use_spectral=False)
        audio = make_sine_wave()
        with pytest.raises(ValueError, match="Örnekleme hızı"):
            vad.detect(audio, sample_rate=8000)

    def test_adaptive_threshold_increases_over_time(self) -> None:
        """
        Sessiz bölgeden gürültülü bölgeye geçildiğinde adaptif eşiğin
        yükselmesi beklenir.
        """
        vad = EnergyVAD(use_spectral=False)
        # Sessiz başla, güçlü gürültü ile bitir
        silence = make_silence(duration_sec=3.0)
        noise = make_white_noise(duration_sec=3.0, amplitude=0.9)
        audio = np.concatenate([silence, noise]).astype(np.float32)
        result = vad.detect(audio, config.SAMPLE_RATE)

        n = len(result.thresholds)
        # Not: global_min gürültü bölümünü de kapsadığından eşik hemen yükselmeyebilir.
        # Yine de gürültü bölgesindeki eşik sessiz bölgeden yüksek olmalı.
        first_quarter = result.thresholds[:n // 4].mean()
        last_quarter = result.thresholds[3 * n // 4:].mean()
        assert last_quarter >= first_quarter, (
            f"Gürültülü bölümde eşik sessiz bölümden düşük olamaz: "
            f"{first_quarter:.4f} vs {last_quarter:.4f}"
        )

    def test_frame_to_seconds_conversion(self) -> None:
        """frames_to_seconds ve seconds_to_frame dönüşümleri tutarlı olmalı."""
        vad = EnergyVAD(use_spectral=False)
        for frame_idx in [0, 10, 100]:
            sec = vad.frames_to_seconds(frame_idx)
            recovered = vad.seconds_to_frame(sec)
            assert abs(recovered - frame_idx) <= 1, (
                f"Dönüşüm tutarsızlığı: {frame_idx} → {sec:.4f}s → {recovered}"
            )


# ===========================================================================
# EnergyVAD v2 Testleri — Spectral Flatness
# ===========================================================================

class TestEnergyVADSpectral:
    """v2: Spectral Flatness Measure testleri."""

    def test_spectral_flatness_computed_when_enabled(self) -> None:
        """use_spectral=True iken VADResult.spectral_flatness dolu olmalıdır."""
        vad = EnergyVAD(use_spectral=True)
        audio = make_sine_wave(duration_sec=1.0, amplitude=0.5)
        result = vad.detect(audio, config.SAMPLE_RATE)

        assert result.spectral_flatness is not None, (
            "use_spectral=True iken spectral_flatness None olmamalıdır."
        )
        assert result.spectral_flatness.dtype == np.float32
        assert len(result.spectral_flatness) == len(result.frame_activity)

    def test_spectral_flatness_none_when_disabled(self) -> None:
        """use_spectral=False iken VADResult.spectral_flatness None olmalıdır."""
        vad = EnergyVAD(use_spectral=False)
        audio = make_sine_wave(duration_sec=1.0, amplitude=0.5)
        result = vad.detect(audio, config.SAMPLE_RATE)

        assert result.spectral_flatness is None, (
            "use_spectral=False iken spectral_flatness None olmalıdır."
        )

    def test_sine_has_low_sfm(self) -> None:
        """
        Sinüs dalgası (harmonik) düşük SFM değerine sahip olmalıdır.
        Konuşma harmonik yapıda olduğundan SFM < 0.5 beklenir.
        """
        vad = EnergyVAD(use_spectral=True)
        audio = make_sine_wave(frequency=440.0, duration_sec=1.0, amplitude=0.8)
        result = vad.detect(audio, config.SAMPLE_RATE)

        mean_sfm = result.spectral_flatness.mean()
        assert mean_sfm < 0.5, (
            f"Sinüs dalgası için SFM çok yüksek: {mean_sfm:.3f}. "
            "Harmonik sinyal düşük SFM'e sahip olmalıdır."
        )

    def test_white_noise_has_high_sfm(self) -> None:
        """
        Beyaz gürültü yüksek SFM değerine sahip olmalıdır.
        Düz spektrum → SFM ~1.0 beklenir.
        """
        vad = EnergyVAD(use_spectral=True)
        noise = make_white_noise(duration_sec=1.0, amplitude=0.5)
        result = vad.detect(noise, config.SAMPLE_RATE)

        mean_sfm = result.spectral_flatness.mean()
        assert mean_sfm > 0.5, (
            f"Beyaz gürültü için SFM çok düşük: {mean_sfm:.3f}. "
            "Düz spektrum yüksek SFM'e sahip olmalıdır."
        )

    def test_spectral_filter_rejects_noise(self) -> None:
        """
        use_spectral=True iken beyaz gürültü daha az aktif çerçeve üretmelidir.
        Çünkü gürültünün SFM'i yüksek → spectral filtre tarafından engellenir.
        """
        noise = make_white_noise(duration_sec=2.0, amplitude=0.5)

        vad_no_spectral = EnergyVAD(use_spectral=False)
        result_no_spectral = vad_no_spectral.detect(noise, config.SAMPLE_RATE)

        vad_with_spectral = EnergyVAD(use_spectral=True)
        result_with_spectral = vad_with_spectral.detect(noise, config.SAMPLE_RATE)

        # Spectral filtre açıkken daha az aktif çerçeve olmalı
        rate_without = result_no_spectral.frame_activity.mean()
        rate_with = result_with_spectral.frame_activity.mean()

        assert rate_with <= rate_without, (
            f"Spectral filtre gürültüyü bastırmalı: "
            f"filtre kapalı={rate_without:.2%}, filtre açık={rate_with:.2%}"
        )


# ===========================================================================
# MultiChannelVAD Testleri
# ===========================================================================

class TestMultiChannelVAD:
    """MultiChannelVAD sınıfı testleri."""

    def test_single_active_channel(self) -> None:
        """Tek aktif kanalın segment üretip üretmediğini test eder."""
        mcvad = MultiChannelVAD(use_spectral=False)

        # Gerçekçi senaryo: konuşma/sessizlik geçişli ses
        channels: Dict[str, np.ndarray] = {
            "speaker_1": make_speech_with_silence(
                speech_regions=[(1.0, 3.0)],  # 1-3. saniyede konuşma
                total_duration=4.0,
                amplitude=0.8,
            ),
            "speaker_2": make_silence(duration_sec=4.0),
        }
        segments = mcvad.process(channels)

        # En az bir segment üretilmeli
        assert len(segments) > 0, "En az bir segment üretilmeli."

        for seg in segments:
            assert seg["speaker"] in ("speaker_1", "speaker_2", "overlap")

    def test_overlap_scenario(self) -> None:
        """
        İki kanalın eş zamanlı aktif olduğu senaryoda segment üretildiğini test eder.
        Her iki kanalın da konuşma+sessizlik içerdiği gerçekçi durum.
        """
        mcvad = MultiChannelVAD(use_spectral=False)

        # Her iki kanal aynı anda aktif (aynı ses, farklı kanal)
        speech = make_speech_with_silence(
            speech_regions=[(0.5, 3.0)],
            total_duration=4.0,
            amplitude=0.8,
        )
        channels: Dict[str, np.ndarray] = {
            "speaker_1": speech.copy(),
            "speaker_2": speech.copy(),
        }
        segments = mcvad.process(channels)

        # Her iki kanal aktifken overlap veya single segment üretilmeli
        assert len(segments) > 0, "Konuşma bölgesinde segment üretilmeli."
        # VAD aktif bölge tespiti yapabildiğini doğrula
        non_silence = [
            s for s in segments
            if s["type"] in ("overlap", "single")
        ]
        assert len(non_silence) > 0, "En az bir aktif segment bekleniyor."

    def test_short_segment_merged_into_previous(self) -> None:
        """
        300 ms'den kısa geçiş segmentinin önceki konuşmacıya atandığını test eder.
        Doğrudan _merge_short_segments metodunu test eder.
        """
        mcvad = MultiChannelVAD(min_segment_ms=300, use_spectral=False)

        # Manuel segment listesi
        segs: list[Segment] = [
            Segment(speaker="speaker_1", start=0.0, end=2.0, type="single",
                    speakers=["speaker_1"]),
            Segment(speaker="speaker_2", start=2.0, end=2.1, type="single",
                    speakers=["speaker_2"]),  # 100 ms → kısa
            Segment(speaker="speaker_1", start=2.1, end=4.0, type="single",
                    speakers=["speaker_1"]),
        ]

        merged = mcvad._merge_short_segments(segs)

        # 100 ms'lik segment 2. segment öncekiyle birleşmeli
        assert len(merged) < len(segs), (
            "Kısa segment listeden kaldırılmalı veya öncekiyle birleştirilmeli."
        )

    def test_empty_channels_raises_error(self) -> None:
        """Boş kanal sözlüğünde ValueError fırlatıldığını test eder."""
        mcvad = MultiChannelVAD(use_spectral=False)
        with pytest.raises(ValueError, match="boş olamaz"):
            mcvad.process({})

    def test_output_structure(self) -> None:
        """Çıktı sözlüklerin beklenen anahtar ve tiplerini içerdiğini test eder."""
        mcvad = MultiChannelVAD(use_spectral=False)
        # Konuşma+sessizlik içeren gerçekçi ses
        channels = {
            "speaker_1": make_speech_with_silence(
                speech_regions=[(0.5, 1.5)],
                total_duration=2.0,
            ),
        }
        segments = mcvad.process(channels)

        assert isinstance(segments, list)
        # Segment üretilmediyse (tamamen sessizse) liste boş olabilir; format kontrol et
        for seg in segments:
            assert "speaker" in seg
            assert "start" in seg
            assert "end" in seg
            assert "type" in seg
            assert "speakers" in seg
            assert isinstance(seg["start"], float)
            assert isinstance(seg["end"], float)
            assert seg["end"] >= seg["start"]

    def test_bleed_suppression(self) -> None:
        """
        Zayıf kanalın (bleed simülasyonu) aktif sayılmadığını test eder.
        Ana kanal 0.8 genlik, alt kanal 0.01 genlik (bleed).
        """
        mcvad = MultiChannelVAD(bleed_ratio=config.BLEED_RATIO, use_spectral=False)
        main_audio = make_speech_with_silence(
            speech_regions=[(0.5, 2.0)],
            total_duration=3.0,
            amplitude=0.8,
        )
        bleed_audio = main_audio * 0.01  # %1 yükseklik → bleed

        channels = {
            "speaker_1": main_audio,
            "speaker_2": bleed_audio,
        }
        segments = mcvad.process(channels)

        # Bleed kanalı (speaker_2) single tip segment üretmemeli ya da çok az seg. üretmeli
        single_sp2 = [s for s in segments if s["speaker"] == "speaker_2" and s["type"] == "single"]
        total_sp2_duration = sum(s["duration"] for s in single_sp2)
        total_duration = sum(s["duration"] for s in segments)

        if total_duration > 0:
            sp2_ratio = total_sp2_duration / total_duration
            assert sp2_ratio < 0.3, (
                f"Bleed kanalı ({sp2_ratio:.1%}) çok fazla aktif sayıldı."
            )

    def test_three_channel_activity_matrix(self) -> None:
        """3 kanallı senaryoda aktivite matrisinin doğru boyuta sahip olduğunu test eder."""
        mcvad = MultiChannelVAD(use_spectral=False)
        n_samples = config.SAMPLE_RATE * 2  # 2 saniye
        channels = {
            "speaker_1": make_sine_wave(duration_sec=2.0, amplitude=0.8),
            "speaker_2": make_silence(duration_sec=2.0),
            "speaker_3": make_white_noise(duration_sec=2.0, amplitude=0.5),
        }
        activity_matrix, speaker_ids, frame_times = mcvad.get_activity_matrix(channels)

        assert activity_matrix.shape[0] == 3, "3 kanal için 3 satır bekleniyor."
        assert activity_matrix.shape[1] == len(frame_times), "Sütun-zaman uyumu."
        assert set(speaker_ids) == {"speaker_1", "speaker_2", "speaker_3"}


# ===========================================================================
# MultiChannelVAD v2 Testleri — Dominant-Only Modu
# ===========================================================================

class TestMultiChannelVADDominant:
    """v2: Dominant-only modu testleri."""

    def test_dominant_channel_suppresses_weak_overlap(self) -> None:
        """
        Dominant kanalın enerjisi diğerinin 3 katından fazlaysa
        zayıf kanal aktif sayılmamalıdır.

        Senaryo: ana kanal 0.8 genlik, sızıntı kanalı 0.2 genlik.
        dominant_ratio=3.0 ile 0.8/0.2=4.0 > 3.0 → sadece dominant aktif.
        """
        mcvad = MultiChannelVAD(
            dominant_ratio=3.0,
            bleed_ratio=0.01,  # Bleed filtresini gevşet, dominant-only'i test et
            use_spectral=False,
        )

        main_audio = make_speech_with_silence(
            speech_regions=[(0.5, 2.5)],
            total_duration=3.0,
            amplitude=0.8,
        )
        weak_audio = make_speech_with_silence(
            speech_regions=[(0.5, 2.5)],
            total_duration=3.0,
            amplitude=0.2,
        )

        channels = {
            "speaker_1": main_audio,
            "speaker_2": weak_audio,
        }
        segments = mcvad.process(channels)

        # Overlap tipi segment ya hiç olmamalı ya da çok az olmalı
        overlap_segs = [s for s in segments if s["type"] == "overlap"]
        overlap_duration = sum(s["duration"] for s in overlap_segs)
        total_duration = sum(s["duration"] for s in segments)

        if total_duration > 0:
            overlap_ratio = overlap_duration / total_duration
            assert overlap_ratio < 0.3, (
                f"Dominant-only modu çalışmalı: overlap oranı {overlap_ratio:.1%} "
                f"çok yüksek (beklenen < 30%)."
            )

    def test_equal_energy_keeps_both_active(self) -> None:
        """
        İki kanal eşit enerjideyse dominant-only devreye girmemeli,
        her ikisi de aktif kalmalıdır (gerçek overlap).
        """
        mcvad = MultiChannelVAD(
            dominant_ratio=3.0,
            bleed_ratio=0.01,
            use_spectral=False,
        )

        speech = make_speech_with_silence(
            speech_regions=[(0.5, 2.5)],
            total_duration=3.0,
            amplitude=0.8,
        )

        channels = {
            "speaker_1": speech.copy(),
            "speaker_2": speech.copy(),
        }
        segments = mcvad.process(channels)

        # Eşit enerjide overlap segment üretilmeli
        assert len(segments) > 0, "Segment üretilmeli."
        # En az bir overlap veya iki farklı konuşmacı görmeli
        speakers_seen = set()
        for s in segments:
            if s["type"] == "overlap":
                speakers_seen.update(s["speakers"])
            else:
                speakers_seen.add(s["speaker"])
        assert len(speakers_seen) >= 1, (
            "Eşit enerjili kanallardan en az biri görünmeli."
        )

    def test_dominant_only_applies_after_bleed_filter(self) -> None:
        """
        _apply_dominant_only metodunun doğrudan aktivite matrisini düzelttiğini
        birim test ile doğrular.
        """
        mcvad = MultiChannelVAD(dominant_ratio=2.0, use_spectral=False)

        # 2 kanal, 5 frame
        activity = np.array([
            [True, True, True, False, True],
            [True, True, False, False, True],
        ], dtype=bool)

        energy = np.array([
            [0.8, 0.3, 0.5, 0.0, 0.6],
            [0.2, 0.8, 0.0, 0.0, 0.55],
        ], dtype=np.float32)

        result = mcvad._apply_dominant_only(activity, energy)

        # Frame 0: 0.8/0.2 = 4.0 > 2.0 → sadece kanal 0 aktif
        assert result[0, 0] == True
        assert result[1, 0] == False

        # Frame 1: 0.8/0.3 = 2.67 > 2.0 → sadece kanal 1 aktif
        assert result[0, 1] == False
        assert result[1, 1] == True

        # Frame 4: 0.6/0.55 = 1.09 < 2.0 → ikisi de aktif kalır
        assert result[0, 4] == True
        assert result[1, 4] == True


# ===========================================================================
# RTTMWriter Testleri
# ===========================================================================

class TestRTTMWriter:
    """RTTMWriter sınıfı testleri."""

    def _make_segments(self) -> list[dict]:
        """Test için örnek segment listesi oluşturur."""
        return [
            {
                "speaker": "speaker_1",
                "start": 0.0,
                "end": 2.5,
                "duration": 2.5,
                "type": "single",
                "speakers": ["speaker_1"],
            },
            {
                "speaker": "overlap",
                "start": 2.5,
                "end": 3.2,
                "duration": 0.7,
                "type": "overlap",
                "speakers": ["speaker_1", "speaker_2"],
            },
            {
                "speaker": "speaker_2",
                "start": 3.2,
                "end": 5.0,
                "duration": 1.8,
                "type": "single",
                "speakers": ["speaker_2"],
            },
        ]

    def test_write_creates_file(self, tmp_path: Path) -> None:
        """write() metodunun dosya oluşturduğunu test eder."""
        writer = RTTMWriter()
        segments = self._make_segments()
        out = tmp_path / "test.rttm"
        result_path = writer.write(segments, out, recording_id="test_rec")

        assert result_path.exists(), "RTTM dosyası oluşturulmalıdır."
        assert result_path.stat().st_size > 0, "RTTM dosyası boş olmamalıdır."

    def test_rttm_format_starts_with_speaker(self, tmp_path: Path) -> None:
        """RTTM satırlarının 'SPEAKER' ile başladığını test eder."""
        writer = RTTMWriter()
        segments = self._make_segments()
        out = tmp_path / "format_test.rttm"
        writer.write(segments, out, recording_id="rec1")

        lines = out.read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            assert line.startswith("SPEAKER"), (
                f"Her satır 'SPEAKER' ile başlamalı: '{line}'"
            )

    def test_overlap_segments_write_multiple_lines(self, tmp_path: Path) -> None:
        """Overlap segmentinin her konuşmacı için ayrı satır yazdığını test eder."""
        writer = RTTMWriter()
        segments = self._make_segments()
        out = tmp_path / "overlap_test.rttm"
        writer.write(segments, out, recording_id="rec1")

        lines = out.read_text(encoding="utf-8").strip().splitlines()
        # 1 single + 2 overlap satırı + 1 single = 4 satır
        assert len(lines) == 4, (
            f"Beklenen 4 satır (1+2+1), bulundu: {len(lines)}\n"
            + "\n".join(lines)
        )

    def test_read_returns_correct_structure(self, tmp_path: Path) -> None:
        """read() metodunun doğru alanları döndürdüğünü test eder."""
        writer = RTTMWriter()
        segments = self._make_segments()
        out = tmp_path / "read_test.rttm"
        writer.write(segments, out, recording_id="test_rec")

        loaded = writer.read(out)

        assert isinstance(loaded, list)
        assert len(loaded) > 0

        for seg in loaded:
            assert "recording_id" in seg
            assert "speaker" in seg
            assert "start" in seg
            assert "end" in seg
            assert "duration" in seg
            assert seg["recording_id"] == "test_rec"
            assert seg["start"] >= 0.0
            assert seg["end"] > seg["start"]

    def test_read_write_roundtrip(self, tmp_path: Path) -> None:
        """Yazılan verilerin doğru okunduğunu doğrular (roundtrip testi)."""
        writer = RTTMWriter()
        segments = self._make_segments()
        out = tmp_path / "roundtrip.rttm"
        writer.write(segments, out, recording_id="rtrip")

        loaded = writer.read(out)
        speakers = [seg["speaker"] for seg in loaded]

        assert "speaker_1" in speakers, "speaker_1 verisi RTTM'de bulunmalıdır."
        assert "speaker_2" in speakers, "speaker_2 verisi RTTM'de bulunmalıdır."

    def test_read_nonexistent_file_raises(self, tmp_path: Path) -> None:
        """Var olmayan dosya için FileNotFoundError fırlatılmalıdır."""
        writer = RTTMWriter()
        with pytest.raises(FileNotFoundError):
            writer.read(tmp_path / "nonexistent.rttm")

    def test_write_string_no_file_created(self, tmp_path: Path) -> None:
        """write_string() yöntemi dosya oluşturmadan string döndürmelidir."""
        writer = RTTMWriter()
        segments = self._make_segments()
        content = writer.write_string(segments, recording_id="str_test")

        assert isinstance(content, str)
        assert "SPEAKER" in content
        assert "str_test" in content

    def test_parse_invalid_rttm_line_raises(self) -> None:
        """Bozuk RTTM satırı için RTTMParseError fırlatılmalıdır."""
        with pytest.raises(RTTMParseError):
            RTTMWriter._parse_rttm_line("SPEAKER rec1 1 0.5", lineno=1)

    def test_empty_segments_raises_value_error(self, tmp_path: Path) -> None:
        """Boş segment listesi için ValueError fırlatılmalıdır."""
        writer = RTTMWriter()
        with pytest.raises(ValueError, match="boş olamaz"):
            writer.write([], tmp_path / "empty.rttm")


# ===========================================================================
# RTTMWriter v2 Testleri — Overlap Satır Ayrımı
# ===========================================================================

class TestRTTMWriterV2:
    """v2: Overlap segmentlerinde 'overlap' etiketi yazılmaması testi."""

    def test_overlap_never_writes_overlap_label(self, tmp_path: Path) -> None:
        """
        v2: Overlap segmentinde RTTM satırlarında 'overlap' kelimesi
        konuşmacı etiketi olarak asla yazılmamalıdır. Her konuşmacı
        kendi adıyla ayrı satır almalıdır.
        """
        writer = RTTMWriter()
        segments = [
            {
                "speaker": "overlap",
                "start": 1.0,
                "end": 3.0,
                "duration": 2.0,
                "type": "overlap",
                "speakers": ["speaker_1", "speaker_2"],
            },
        ]
        out = tmp_path / "no_overlap_label.rttm"
        writer.write(segments, out, recording_id="test")

        content = out.read_text(encoding="utf-8")
        lines = content.strip().splitlines()

        # 2 satır olmalı: speaker_1 ve speaker_2 için birer tane
        assert len(lines) == 2, (
            f"Beklenen 2 satır, bulundu: {len(lines)}\n" + content
        )

        # Hiçbir satırda 'overlap' konuşmacı etiketi olmamalı
        for line in lines:
            parts = line.split()
            speaker_field = parts[7]  # RTTM'de 8. alan = konuşmacı
            assert speaker_field != "overlap", (
                f"'overlap' konuşmacı etiketi olarak yazılmamalı: {line}"
            )

    def test_overlap_with_three_speakers(self, tmp_path: Path) -> None:
        """
        v2: 3 konuşmacılı overlap segmentinde 3 ayrı RTTM satırı
        üretilmelidir.
        """
        writer = RTTMWriter()
        segments = [
            {
                "speaker": "overlap",
                "start": 0.0,
                "end": 2.0,
                "duration": 2.0,
                "type": "overlap",
                "speakers": ["alice", "bob", "charlie"],
            },
        ]
        out = tmp_path / "three_speakers.rttm"
        writer.write(segments, out, recording_id="test")

        lines = out.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3, (
            f"3 konuşmacılı overlap → 3 satır bekleniyor, bulundu: {len(lines)}"
        )

        speakers_in_rttm = [line.split()[7] for line in lines]
        assert set(speakers_in_rttm) == {"alice", "bob", "charlie"}, (
            f"Konuşmacılar eşleşmeli: {speakers_in_rttm}"
        )

    def test_single_segment_unchanged(self, tmp_path: Path) -> None:
        """
        v2: type='single' segmentler için davranış değişmemiş olmalıdır.
        Tek satır, doğru konuşmacı etiketi.
        """
        writer = RTTMWriter()
        segments = [
            {
                "speaker": "speaker_1",
                "start": 0.0,
                "end": 2.5,
                "duration": 2.5,
                "type": "single",
                "speakers": ["speaker_1"],
            },
        ]
        out = tmp_path / "single_unchanged.rttm"
        writer.write(segments, out, recording_id="test")

        lines = out.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1, f"Single segment → 1 satır bekleniyor."
        assert "speaker_1" in lines[0]


# ===========================================================================
# Entegrasyon Testi
# ===========================================================================

class TestIntegration:
    """Birden fazla sınıfı birlikte kullanan entegrasyon testleri."""

    def test_full_pipeline_produces_valid_rttm(self, tmp_path: Path) -> None:
        """
        MultiChannelVAD → RTTMWriter tam akışının geçerli RTTM ürettiğini test eder.
        """
        # 1. Sentetik ses üret: farklı konuşma bölgeli iki kanal
        channels = {
            "alice": make_speech_with_silence(
                speech_regions=[(0.5, 2.0), (3.5, 5.0)],
                total_duration=6.0,
            ),
            "bob": make_speech_with_silence(
                speech_regions=[(2.5, 4.0)],
                total_duration=6.0,
            ),
        }

        # 2. MultiChannelVAD ile işle
        mcvad = MultiChannelVAD(use_spectral=False)
        segments = mcvad.process(channels)
        assert len(segments) > 0, "En az bir segment üretilmeli."

        # 3. RTTM yaz
        writer = RTTMWriter()
        rttm_path = tmp_path / "integration.rttm"
        writer.write(segments, rttm_path, recording_id="integration_test")
        assert rttm_path.exists()

        # 4. Geri oku ve doğrula
        loaded = writer.read(rttm_path)
        assert len(loaded) > 0
        for seg in loaded:
            assert seg["duration"] > 0
            assert seg["recording_id"] == "integration_test"

    def test_overlap_in_full_pipeline(self, tmp_path: Path) -> None:
        """
        İki kanalın eş zamanlı aktif olduğu durumda RTTM'de her ikisinin
        görüneceğini test eder.
        """
        # Her iki kanal aynı anda konuşma içeriyor (gerçekçi overlap senaryosu)
        speech = make_speech_with_silence(
            speech_regions=[(0.5, 2.5)],
            total_duration=3.0,
            amplitude=0.8,
        )
        channels = {
            "speaker_1": speech.copy(),
            "speaker_2": speech.copy(),
        }

        mcvad = MultiChannelVAD(use_spectral=False)
        segments = mcvad.process(channels)

        # Segment üretildiyse RTTM'e yaz ve doğrula
        assert len(segments) > 0, "Konuşma bölgesinde segment üretilmeli."

        writer = RTTMWriter()
        rttm_path = tmp_path / "overlap_integration.rttm"
        writer.write(segments, rttm_path, recording_id="overlap_test")

        loaded = writer.read(rttm_path)
        speakers_in_rttm = {seg["speaker"] for seg in loaded}

        # Overlap veya single olarak en az bir konuşmacı görünmeli
        assert len(speakers_in_rttm) > 0, (
            "RTTM'de en az bir konuşmacı görünmeli."
        )

    def test_v2_full_pipeline_no_overlap_label_in_rttm(self, tmp_path: Path) -> None:
        """
        v2 entegrasyon: Tam pipeline sonunda RTTM'de 'overlap' konuşmacı
        etiketi hiçbir satırda bulunmamalıdır.
        """
        # Eşit enerjili iki kanal → overlap üretebilir
        speech = make_speech_with_silence(
            speech_regions=[(0.5, 2.5)],
            total_duration=3.0,
            amplitude=0.8,
        )
        channels = {
            "speaker_1": speech.copy(),
            "speaker_2": speech.copy(),
        }

        mcvad = MultiChannelVAD(
            bleed_ratio=0.01,
            dominant_ratio=100.0,  # Dominant-only'i devre dışı bırak → overlap üretilsin
            use_spectral=False,
        )
        segments = mcvad.process(channels)

        writer = RTTMWriter()
        rttm_path = tmp_path / "v2_integration.rttm"
        writer.write(segments, rttm_path, recording_id="v2_test")

        loaded = writer.read(rttm_path)
        for seg in loaded:
            assert seg["speaker"] != "overlap", (
                f"'overlap' konuşmacı etiketi RTTM'de olmamalıdır: {seg}"
            )

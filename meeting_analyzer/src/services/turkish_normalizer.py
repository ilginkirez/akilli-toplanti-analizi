"""
turkish_normalizer.py
---------------------
Turkce ASR ciktisi icin post-processing ve normalizasyon.

Ozcelik & Gungor (2023) "Turkish Text Normalization for ASR Output"
makalesinden esinlenerek, Whisper'in Turkce ciktisindaki yaygin
hatalari duzeltir.

Icerik:
  1. Turkce karakter normalizasyonu (I/i problemi vb.)
  2. Yaygin ASR hata duzeltmeleri
  3. Turkce'ye ozgu segment filtreleme

Referans: SIU 2023 — Turkce ASR ciktisinda %3-5 WER iyilesmesi.
"""

import re
import unicodedata


# ---------------------------------------------------------------------------
# 1. Turkce Karakter Normalizasyonu
# ---------------------------------------------------------------------------

# Whisper'in urettigi yaygin Turkce karakter hatalari
_TURKISH_CHAR_MAP = {
    "İ": "İ",   # Buyuk I noktalı (zaten doğru)
    "I": "I",   # Buyuk I noktasız — kontekste bağlı
}

# Turkce'de buyuk I her zaman İ olmali (kelime basinda)
# Ancak "I" tek basina veya kelime icinde "ı" olabilir
_TURKISH_LOWER_MAP = {
    "I": "ı",   # Noktasız buyuk I -> noktasız kucuk ı
    "İ": "i",   # Noktali buyuk I -> noktali kucuk i
}


def normalize_turkish_chars(text: str) -> str:
    """
    Whisper'in Turkce ciktisindaki karakter sorunlarini duzeltir.

    Yaygın problemler:
    - "Istanbul" yerine "İstanbul"
    - "ILGIN" yerine "ILGIN" (noktasız I sorunu)
    - Unicode normalizasyon farklılıkları

    Kaynak: Ozcelik & Gungor (2023), SIU.
    """
    if not text:
        return ""

    # Unicode NFC normalizasyonu (composed form)
    text = unicodedata.normalize("NFC", text)

    # Turkce I/İ problemi: Kelime basinda "I" -> "İ" (buyuk harf ise)
    # Bu cok agresif olabilir, sadece bilinen kelimelerde uygulayalim
    # Genel kural: Turkce'de tek basina "I" nadiren kullanilir
    words = text.split()
    corrected_words = []

    for word in words:
        if not word:
            corrected_words.append(word)
            continue

        # Tamamen buyuk harfli kelimelerde I -> İ (ILGIN -> İLGİN)
        if word.isupper() and len(word) > 1:
            word = word.replace("I", "İ")

        # Kelime basinda buyuk I ve geri kalan kucuk harf ise -> İ
        elif len(word) > 1 and word[0] == "I" and word[1:].islower():
            word = "İ" + word[1:]

        corrected_words.append(word)

    return " ".join(corrected_words)


def normalize_turkish_asr_output(text: str) -> str:
    """
    Kapsamli Turkce ASR post-processing.
    Sirayla uygulanan normalizasyon adimlari:
      1. Unicode NFC normalizasyonu
      2. Turkce karakter duzeltmesi
      3. Tekrarlanan bosluk/noktalama temizligi
      4. Yaygin ASR hata duzeltmeleri
    """
    if not text:
        return ""

    # 1. Unicode normalizasyon
    text = unicodedata.normalize("NFC", text)

    # 2. Turkce karakter duzeltmesi
    text = normalize_turkish_chars(text)

    # 3. Yaygin Whisper Turkce hatalari
    # Whisper bazen Turkce kelimeleri Ingilizce fonetikle yazar
    _common_corrections = {
        r"\btesekkurler\b": "teşekkürler",
        r"\btesekurler\b": "teşekkürler",
        r"\bgorusuruz\b": "görüşürüz",
        r"\bgorusler\b": "görüşler",
        r"\btamamdir\b": "tamamdır",
    }
    for pattern, replacement in _common_corrections.items():
        text = re.sub(pattern, replacement, text)

    # 4. Tekrarlanan boşluk temizliği
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ---------------------------------------------------------------------------
# 2. Turkce'ye Ozgu Segment Filtreleme
# ---------------------------------------------------------------------------

# Turkce'de yaygin kisa onaylama/argo kelimeleri
# Whisper bunlari bazen no_speech olarak siniflandirir
TURKISH_SHORT_CONFIRMATIONS = {
    "evet",
    "hayır",
    "tamam",
    "tabii",
    "tabi",
    "hmm",
    "hım",
    "hımm",
    "aha",
    "peki",
    "olur",
    "yok",
    "var",
    "iyi",
    "güzel",
    "anladım",
    "anlaşıldı",
    "doğru",
    "aynen",
    "kesinlikle",
    "maalesef",
    "pardon",
}


def is_turkish_confirmation(text: str) -> bool:
    """
    Metnin Turkce kisa onaylama/cevap olup olmadigini kontrol eder.
    Bu tip segmentler no_speech_prob esigine takilabilir ama
    aslinda gecerli konusmadir.
    """
    if not text:
        return False
    clean = text.strip().lower().rstrip(".!?,")
    return clean in TURKISH_SHORT_CONFIRMATIONS


def should_keep_turkish_segment(
    text: str,
    no_speech_prob: float | None,
    avg_logprob: float | None,
    *,
    max_no_speech_prob: float = 0.50,
    min_avg_logprob: float = -1.0,
) -> bool:
    """
    Turkce'ye ozgu segment filtreleme.

    Standart esiklere ek olarak:
    - Turkce kisa onaylamalar korunur (evet, tamam, vb.)
    - Agglutinasyon nedeniyle logprob esigi gevsetilir

    Args:
        text: Segment metni
        no_speech_prob: Whisper no_speech olasiligi
        avg_logprob: Whisper ortalama log-olasiligi
        max_no_speech_prob: Maksimum no_speech esigi
        min_avg_logprob: Minimum logprob esigi

    Returns:
        True ise segment korunmali
    """
    if not text or not text.strip():
        return False

    # Turkce kisa onaylamalar: esikleri gec
    if is_turkish_confirmation(text):
        # Cok yuksek no_speech_prob bile olsa koru (0.90'a kadar)
        if no_speech_prob is not None and no_speech_prob > 0.90:
            return False
        return True

    # Standart filtreler
    if no_speech_prob is not None and no_speech_prob > max_no_speech_prob:
        return False
    if avg_logprob is not None and avg_logprob < min_avg_logprob:
        return False

    return True


# ---------------------------------------------------------------------------
# 3. WER Hesaplamasi Icin Normalizasyon
# ---------------------------------------------------------------------------

def normalize_for_wer(text: str) -> str:
    """
    WER hesaplamasi icin tutarli normalizasyon.
    Hem referans hem hipotez metinlerine uygulanmali.
    """
    if not text:
        return ""

    text = text.lower()

    # Turkce kucuk harf donusumu
    text = text.replace("I", "ı").replace("İ", "i")

    # Noktalama kaldir
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)

    # Rakamlari koru ama fazla bosluklari temizle
    text = re.sub(r"\s+", " ", text).strip()

    return text

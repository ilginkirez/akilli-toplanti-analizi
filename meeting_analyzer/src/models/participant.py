from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ParticipantMetadata(BaseModel):
    participant_id: str        # UUID - sistem uretir
    display_name: str          # Kullanicinin girdigi isim
    session_id: str
    connection_id: Optional[str] = None   # WebRTC baglanti ID
    stream_id: Optional[str] = None       # Medya stream ID
    join_time: datetime
    leave_time: Optional[datetime] = None

    # Cihaz bilgisi - tezde analiz icin
    device_type: str           # "mobile" | "desktop" | "tablet"
    browser: str               # "chrome" | "firefox" | "safari" | "other"
    os: str                    # "windows" | "macos" | "android" | "ios" | "other"

    # Akustik kosullar - tezde kontrol degiskeni
    audio_device: str          # "headset" | "speaker" | "unknown"
    room_condition: str        # "same_room" | "separate_room" | "unknown"
    network_type: str          # "wifi" | "ethernet" | "cellular" | "unknown"
    network_notes: Optional[str] = None

    # Kayit bilgisi
    recording_file: Optional[str] = None  # dosya adi
    stream_recording_id: Optional[str] = None  # Kayit sistemi tarafindaki ID

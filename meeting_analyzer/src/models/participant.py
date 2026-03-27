from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ParticipantMetadata(BaseModel):
    participant_id: str        # UUID — sistem üretir
    display_name: str          # Kullanıcının girdiği isim
    session_id: str
    connection_id: Optional[str] = None   # OpenVidu bağlantı ID
    stream_id: Optional[str] = None       # OpenVidu stream ID
    join_time: datetime
    leave_time: Optional[datetime] = None
    
    # Cihaz bilgisi — tezde analiz için
    device_type: str           # "mobile" | "desktop" | "tablet"
    browser: str               # "chrome" | "firefox" | "safari" | "other"
    os: str                    # "windows" | "macos" | "android" | "ios" | "other"
    
    # Akustik koşullar — tezde kontrol değişkeni
    audio_device: str          # "headset" | "speaker" | "unknown"
    room_condition: str        # "same_room" | "separate_room" | "unknown"
    network_type: str          # "wifi" | "ethernet" | "cellular" | "unknown"
    network_notes: Optional[str] = None
    
    # Kayıt bilgisi
    recording_file: Optional[str] = None  # dosya adı
    stream_recording_id: Optional[str] = None  # OpenVidu recording ID

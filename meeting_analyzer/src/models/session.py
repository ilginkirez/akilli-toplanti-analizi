from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .participant import ParticipantMetadata

class SessionMetadata(BaseModel):
    session_id: str
    created_at: datetime
    finalized_at: Optional[datetime] = None
    participants: List[ParticipantMetadata] = []
    total_duration_sec: Optional[float] = None
    dataset_path: Optional[str] = None

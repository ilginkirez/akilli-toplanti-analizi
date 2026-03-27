from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime

class EventLog(BaseModel):
    event: str
    timestamp: datetime
    session_id: str
    participant_id: Optional[str] = None
    details: Dict[str, Any] = {}

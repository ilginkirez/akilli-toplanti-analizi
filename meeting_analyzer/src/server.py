from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import dataset, events, livekit, meetings, participants, recordings, sessions
from .services import livekit_service
from .services.session_store import session_store

app = FastAPI(title="Smart Meeting API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

app.include_router(sessions.router,      prefix="/api/sessions", tags=["Sessions"])
app.include_router(meetings.router,      prefix="/api/meetings", tags=["Meetings"])
app.include_router(participants.router,  prefix="/api/participants", tags=["Participants"])
app.include_router(recordings.router,    prefix="/api/recordings", tags=["Recordings"])
app.include_router(events.router,        prefix="/api/sessions", tags=["Events"])
app.include_router(livekit.router,       prefix="/api/livekit", tags=["LiveKit"])
app.include_router(dataset.router,       prefix="/api/dataset", tags=["Dataset"])

@app.get("/")
def read_root():
    return {"message": "Smart Meeting Platform Backend Running"}

@app.get("/api/health")
def health_check():
    session_count = sum(
        1
        for session_dir in session_store.sessions_dir.iterdir()
        if session_dir.is_dir()
    )
    return {
        "status": "ok",
        "livekit_connected": livekit_service.is_configured(),
        "rtc_provider": "livekit",
        "active_sessions": session_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

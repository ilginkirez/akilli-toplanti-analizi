from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.tasks.audio_processor import process_audio
from src.services.audio_leakage_detector import AudioLeakageDetector
import time
import os
from pathlib import Path

router = APIRouter()
leakage_detector = AudioLeakageDetector()

@router.websocket("/ws/audio/{session_id}/{participant_id}")
async def audio_stream(websocket: WebSocket, session_id: str, participant_id: str):
    await websocket.accept()
    print(f"🔌 {participant_id} bağlandı (Oturum: {session_id})")
    
    audio_dir = Path(f"/tmp/{session_id}")
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            
            timestamp = time.time()
            audio_path = str(audio_dir / f"{participant_id}_{timestamp}.wav")
            
            with open(audio_path, "wb") as f:
                f.write(audio_chunk)
            
            task = process_audio.delay(
                audio_path=audio_path,
                participant_id=participant_id,
                session_id=session_id,
                timestamp=timestamp
            )
            
            await websocket.send_json({
                "status": "queued",
                "task_id": task.id,
                "message": "Ses işleme kuyruğuna alındı"
            })
            
    except WebSocketDisconnect:
        print(f"❌ {participant_id} bağlantısı kesildi")
    except Exception as e:
        print(f"❌ Hata: {e}")
        await websocket.close()

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    from src.celery_app import celery_app
    task = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None
    }

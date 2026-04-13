from celery import Task
from src.celery_app import celery_app
import torch
import whisper
import json
import time
from pathlib import Path

class AudioProcessorTask(Task):
    _vad_model = None
    _asr_model = None
    
    @property
    def vad_model(self):
        if self._vad_model is None:
            self._vad_model = torch.hub.load('snakers4/silero-vad', 'silero-vad')
        return self._vad_model
    
    @property
    def asr_model(self):
        if self._asr_model is None:
            self._asr_model = whisper.load_model("base")
        return self._asr_model

@celery_app.task(bind=True, base=AudioProcessorTask, max_retries=3)
def process_audio(self, audio_path: str, participant_id: str, session_id: str, timestamp: float):
    try:
        print(f"🔄 İşleniyor: {participant_id} - {audio_path}")
        
        # VAD
        speech_timestamps = self.vad_model(audio_path, return_seconds=True)
        
        if not speech_timestamps:
            return {"status": "no_speech", "participant_id": participant_id}
        
        # ASR
        result = self.asr_model.transcribe(audio_path)
        
        output = {
            "session_id": session_id,
            "participant_id": participant_id,
            "timestamp": timestamp,
            "transcription": result["text"],
            "speech_segments": speech_timestamps,
            "asr_confidence": result.get("confidence", 0.9)
        }
        
        print(f"✅ Tamamlandı: {participant_id}")
        return output
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        self.retry(countdown=5, exc=e)

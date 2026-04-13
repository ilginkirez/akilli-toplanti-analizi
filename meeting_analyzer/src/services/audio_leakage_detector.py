from typing import Dict, List, Optional
import time

class AudioLeakageDetector:
    def __init__(self, similarity_threshold: float = 0.85):
        self.recent_transcriptions: Dict[str, Dict] = {}
        self.similarity_threshold = similarity_threshold
        
    def detect_leakage(self, participant_id: str, transcription: str, timestamp: float) -> Dict:
        for other_id, other_data in self.recent_transcriptions.items():
            if other_id == participant_id:
                continue
                
            time_diff = timestamp - other_data['timestamp']
            if 0.1 < time_diff < 2.0:
                similarity = self._text_similarity(transcription, other_data['transcription'])
                
                if similarity > self.similarity_threshold:
                    print(f"🚨 SES SIZINTISI: {other_id} → {participant_id} (Benzerlik: {similarity:.2%})")
                    return {
                        "is_leakage": True,
                        "source": other_id,
                        "confidence": similarity
                    }
        
        self.recent_transcriptions[participant_id] = {
            'transcription': transcription,
            'timestamp': timestamp
        }
        
        return {"is_leakage": False}
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0
    
    def cleanup_old_entries(self, max_age: float = 5.0):
        current_time = time.time()
        self.recent_transcriptions = {
            pid: data for pid, data in self.recent_transcriptions.items()
            if current_time - data['timestamp'] < max_age
        }

class TaskAssigner:
    @staticmethod
    def calculate_confidence(item: Dict) -> float:
        confidence_score = 1.0
        
        if item.get('is_leakage'):
            confidence_score *= 0.3
            
        if item.get('vad_confidence', 1.0) < 0.7:
            confidence_score *= 0.5
            
        if item.get('asr_confidence', 1.0) < 0.8:
            confidence_score *= 0.7
            
        if len(item.get('transcription', '').split()) < 3:
            confidence_score *= 0.4
        
        return confidence_score
    
    @staticmethod
    def assign_tasks(session_transcriptions: List[Dict]) -> List[Dict]:
        results = []
        
        for item in session_transcriptions:
            confidence_score = TaskAssigner.calculate_confidence(item)
            
            results.append({
                'participant_id': item['participant_id'],
                'transcription': item['transcription'],
                'confidence_score': confidence_score,
                'reliable': confidence_score > 0.5
            })
        
        return [r for r in results if r['reliable']]

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .ai_llm_client import DEFAULT_MODEL, LLMError, GroqLLM
from .ai_agents import build_meeting_analysis_graph
from .ai_output_models import MeetingSummaryOutput, build_meeting_summary_output
from .participant_identity import is_system_participant
from .ai_transcription import (
    TranscriptionError,
    transcribe_audio_clip_text,
    transcribe_audio_segments,
)
from .ai_transcription import (
    TranscriptionError,
    transcribe_audio_clip_text,
    transcribe_audio_segments,
)
from .meeting_store import meeting_store
from .session_store import session_store


logger = logging.getLogger("meeting_analyzer.ai_analysis")


LOCAL_SEGMENT_MERGE_GAP_SEC = 0.5
LOCAL_TRANSCRIPTION_CLIP_PAD_SEC = 0.35


class AIAnalysisError(Exception):
    pass


@dataclass
class ParticipantAudioSource:
    participant_id: str
    display_name: str
    absolute_path: Path
    relative_path: str
    start_offset_sec: float
    source_index: int


@dataclass
class TranscriptWindow:
    participant_id: str
    display_name: str
    start_sec: float
    end_sec: float
    source_segment_ids: list[int]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


class AIAnalysisService:
    def __init__(
        self,
        recordings_dir: Optional[str] = None,
        llm: GroqLLM | None = None,
    ) -> None:
        self.recordings_dir = Path(recordings_dir or session_store.recordings_dir)
        self.llm = llm
        self.analysis_graph = build_meeting_analysis_graph(self)

    def analyze_session(self, session_id: str, *, force: bool = False) -> dict[str, Any]:
        session = session_store.load_session(session_id)
        current = session.get("ai_analysis", {})
        if not force:
            if current.get("status") == "processing":
                return current
            if not self._should_run(session):
                return current

        processing_payload = {
            "status": "processing",
            "generated_at": None,
            "provider": "groq",
            "model": self._model_name(),
            "error": None,
        }
        session_store.update_ai_analysis(session_id, processing_payload)

        try:
            sources = self._collect_sources(session)
            if not sources:
                raise AIAnalysisError("AI analizi icin uygun ses kaydi bulunamadi.")

            graph_state = self._run_analysis_graph(
                session_id=session_id,
                session=session,
                sources=sources,
                meeting_date=self._resolve_meeting_date(session),
            )
            transcript_segments = graph_state.get("transcript_segments") or []
            full_text = str(graph_state.get("full_text") or "")
            if not full_text.strip():
                raise AIAnalysisError("Anlamli transkript olusturulamadi.")
            summary_output = graph_state.get("summary_output")
            if not isinstance(summary_output, MeetingSummaryOutput):
                summary_result = graph_state.get("summary_result") or {}
                action_items = graph_state.get("action_items") or []
                summary_output = build_meeting_summary_output(
                    executive_summary=summary_result.get("executiveSummary", ""),
                    key_decisions=summary_result.get("keyDecisions", []),
                    action_items=action_items,
                    topics=summary_result.get("topics", []),
                )

            analysis_dir = self.recordings_dir / session_id / "analysis" / "ai"
            analysis_dir.mkdir(parents=True, exist_ok=True)

            generated_at = _utc_now_iso()
            transcript_payload = {
                "session_id": session_id,
                "generated_at": generated_at,
                "full_text": full_text,
                "segments": transcript_segments,
                "sources": [
                    {
                        "participant_id": item.participant_id,
                        "display_name": item.display_name,
                        "file_path": item.relative_path,
                        "start_offset_sec": item.start_offset_sec,
                    }
                    for item in sources
                ],
            }
            summary_payload = {
                "session_id": session_id,
                "generated_at": generated_at,
                **summary_output.model_dump(mode="json"),
            }

            transcript_path = analysis_dir / "transcript.json"
            summary_path = analysis_dir / "summary.json"
            transcript_path.write_text(
                json.dumps(transcript_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            summary_path.write_text(
                json.dumps(summary_payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            payload = {
                "status": "ready",
                "generated_at": generated_at,
                "provider": "groq",
                "model": self._model_name(),
                "transcript_path": transcript_path.relative_to(self.recordings_dir).as_posix(),
                "transcript_segment_count": len(transcript_segments),
                "transcript_char_count": len(full_text),
                "summary_path": summary_path.relative_to(self.recordings_dir).as_posix(),
                "executive_summary": summary_output.executiveSummary,
                "key_decisions": summary_output.keyDecisions,
                "topics": summary_output.topics,
                "action_items": [
                    item.model_dump(mode="json")
                    for item in summary_output.actionItems
                ],
                "error": None,
                "completed": [
                    "transcription_agent",
                    "summary_agent",
                    "action_item_agent",
                ],
            }
            session_store.update_ai_analysis(session_id, payload)
            logger.info(
                "[session_id=%s] AI analizi tamamlandi: %d transcript segmenti, %d action item",
                session_id,
                len(transcript_segments),
                len(summary_output.actionItems),
            )
            return payload
        except (AIAnalysisError, LLMError, TranscriptionError, FileNotFoundError) as exc:
            error_payload = {
                "status": "failed",
                "generated_at": _utc_now_iso(),
                "provider": "groq",
                "model": self._model_name(),
                "error": str(exc),
                "completed": [],
            }
            session_store.update_ai_analysis(session_id, error_payload)
            logger.warning("[session_id=%s] AI analizi basarisiz: %s", session_id, exc)
            raise AIAnalysisError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover
            error_payload = {
                "status": "failed",
                "generated_at": _utc_now_iso(),
                "provider": "groq",
                "model": self._model_name(),
                "error": f"beklenmeyen hata: {exc}",
                "completed": [],
            }
            session_store.update_ai_analysis(session_id, error_payload)
            logger.exception("[session_id=%s] AI analizi beklenmeyen hata ile sonlandi", session_id)
            raise AIAnalysisError(str(exc)) from exc

    def _should_run(self, session: dict[str, Any]) -> bool:
        ai_analysis = session.get("ai_analysis", {})
        speech_analysis = session.get("speech_analysis", {})

        ai_generated_at = _parse_iso(ai_analysis.get("generated_at"))
        speech_generated_at = _parse_iso(speech_analysis.get("generated_at"))

        if ai_analysis.get("status") in {"pending", "failed"}:
            return True
        if not ai_generated_at:
            return True
        if speech_generated_at and ai_generated_at < speech_generated_at:
            return True
        if ai_analysis.get("status") != "ready":
            return True
        if not ai_analysis.get("transcript_path") or not ai_analysis.get("summary_path"):
            return True
        return False

    def _run_analysis_graph(
        self,
        *,
        session_id: str,
        session: dict[str, Any],
        sources: list[ParticipantAudioSource],
        meeting_date: str,
    ) -> dict[str, Any]:
        return self.analysis_graph.invoke(
            {
                "session_id": session_id,
                "session": session,
                "sources": sources,
                "meeting_date": meeting_date,
            }
        )

    def _resolve_meeting_date(self, session: dict[str, Any]) -> str:
        meeting_id = session.get("meeting_id")
        if meeting_id:
            meeting = meeting_store.get_meeting(meeting_id)
            if meeting and meeting.get("scheduled_start"):
                return str(meeting["scheduled_start"]).split("T", 1)[0]

        recording_started_at = session.get("recording", {}).get("started_at")
        if recording_started_at:
            return str(recording_started_at).split("T", 1)[0]
        return ""

    def _model_name(self) -> str:
        if self.llm is not None:
            return self.llm.model
        return (os.getenv("GROQ_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL

    def _llm(self) -> GroqLLM:
        return self.llm or GroqLLM()

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


ai_analysis_service = AIAnalysisService()

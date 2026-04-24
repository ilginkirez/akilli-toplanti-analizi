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
from .meeting_store import meeting_store
from .session_store import session_store


logger = logging.getLogger("meeting_analyzer.ai_analysis")

MAX_TOPICS = 5
MAX_DECISIONS = 5

SUMMARY_SYSTEM_PROMPT = """
Sen bir toplanti ozetleme ajanisin.
Sadece verilen transcript ve segmentlere dayan.
Tum ciktilar Turkce olsun.
Uydurma bilgi, yorum veya transcriptte gecmeyen karar ekleme.
Her zaman gecerli JSON don.
Tum alanlar her zaman mevcut olsun.

Kurallar:
- Sadece transcriptte acikca gecen bilgiye dayan.
- executiveSummary 2 ila 4 cumle olsun; kisa, yogun ve yonetici seviyesi bir ozet yaz.
- executiveSummary icine yeni karar, gorev veya tarih uydurma.
- keyDecisions yalnizca toplantida acikca alinmis kararlar icersin.
- Acik karar yoksa keyDecisions bos liste olsun.
- topics sadece ana konulari icersin; kisa basliklar kullan.
- topics en fazla 5 madde olsun.
- Tekrar eden veya anlami ayni olan maddeleri birlestir.
- Belirsiz, varsayimsal veya yoruma dayali madde ekleme.
- JSON disinda hicbir metin yazma.

Beklenen JSON:
{
  "executiveSummary": "2-4 cumlelik yonetici ozeti",
  "keyDecisions": ["karar 1", "karar 2"],
  "topics": ["konu 1", "konu 2"]
}
""".strip()

ACTION_ITEM_SYSTEM_PROMPT = """
Sen bir toplanti aksiyon maddesi cikarma ajanisin.
Sadece verilen transcript ve segmentlerde acikca gecen veya guclu bicimde desteklenen gorevleri cikar.
Tum ciktilar Turkce olsun.
Uydurma gorev, kisi, oncelik veya tarih ekleme.
Eger acik gorev yoksa bos liste don.
Her zaman gecerli JSON don.
Tum alanlar her zaman mevcut olsun.

Kurallar:
- Her action item kisa, net ve uygulanabilir olsun.
- Ayni gorevi farkli sekilde tekrar etme.
- assignee sadece transcriptte aciksa yaz; degilse bos string don.
- due_date sadece transcriptte acik ve kesin bir takvim tarihi varsa doldur.
- Goreli tarih ifadelerini takvim tarihine cevirme: yarin, haftaya, cuma, ay sonu gibi ifadelerde due_date bos string olsun.
- meeting_date bilgisinden tarih turetme.
- priority sadece transcriptte net bicimde anlasiliyorsa doldur; aksi halde bos string don.
- Confidence 0.0 ile 1.0 arasinda olsun.
- Confidence 0.65'ten kucukse needs_review true olsun, degilse false olsun.
- Type alani sadece su degerlerden biri olsun: direct, volunteer, implicit, conditional, group.
- direct: gorev bir kisiye dogrudan verildi.
- volunteer: kisi gorevi kendi ustlendi.
- implicit: yapilacak is var ama atama veya talimat dolayli.
- conditional: gorev bir kosula bagli.
- group: gorev ekip ya da grup icin ortak.
- Yorum, tahmin veya baglamdan cikarimla yeni detay ekleme.
- JSON disinda hicbir metin yazma.

Beklenen JSON:
{
  "action_items": [
    {
      "task": "string",
      "assignee": "string",
      "due_date": "YYYY-MM-DD veya bos string",
      "priority": "low|medium|high|critical veya bos string",
      "confidence": 0.0,
      "type": "direct|volunteer|implicit|conditional|group",
      "needs_review": true
    }
  ]
}
""".strip()

VALID_PRIORITIES = {"", "low", "medium", "high", "critical"}
VALID_ACTION_ITEM_TYPES = {"direct", "volunteer", "implicit", "conditional", "group"}
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


def _normalize_summary_text(value: Any, max_length: int = 1000) -> str:
    return " ".join(str(value or "").strip().split())[:max_length].strip()


def _normalize_string_list(
    items: Any,
    *,
    limit: int,
    max_item_length: int = 120,
) -> list[str]:
    if not isinstance(items, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()

    for item in items:
        text = " ".join(str(item).strip().split())
        if not text:
            continue

        text = text[:max_item_length].strip(" ,;:-")
        if not text:
            continue

        key = text.casefold()
        if key in seen:
            continue

        seen.add(key)
        normalized.append(text)
        if len(normalized) >= limit:
            break

    return normalized


def _normalize_due_date(value: str) -> str:
    if not value:
        return ""

    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _normalize_priority(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in VALID_PRIORITIES else ""


def _normalize_action_item_type(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in VALID_ACTION_ITEM_TYPES:
        return normalized
    return "implicit"


def _normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return round(max(0.0, min(1.0, confidence)), 2)


def _normalize_text(value: Any, max_length: int = 240) -> str:
    return " ".join(str(value or "").strip().split())[:max_length].strip(" ,;:-")


def _should_mark_for_review(item: dict[str, Any], confidence: float) -> bool:
    if confidence < 0.65:
        return True
    return bool(item.get("needs_review", False))


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

    def _collect_sources(self, session: dict[str, Any]) -> list[ParticipantAudioSource]:
        sources: list[ParticipantAudioSource] = []

        for participant in session.get("participants", []):
            if is_system_participant(participant):
                continue
            participant_id = participant.get("participant_id")
            if not participant_id:
                continue

            recording = self._pick_latest_audio_file(participant.get("recording_files") or [])
            if not recording:
                continue

            relative_path = recording.get("file_path")
            if not relative_path:
                continue

            absolute_path = self.recordings_dir / relative_path
            if not absolute_path.exists():
                continue

            start_offset_sec = round(
                float(recording.get("start_time_offset_ms") or 0) / 1000.0,
                4,
            )
            sources.append(
                ParticipantAudioSource(
                    participant_id=participant_id,
                    display_name=participant.get("display_name") or participant_id,
                    absolute_path=absolute_path,
                    relative_path=relative_path,
                    start_offset_sec=start_offset_sec,
                    source_index=int(recording.get("_source_index") or 0),
                )
            )

        return sorted(
            sources,
            key=lambda item: (item.start_offset_sec, item.display_name.casefold(), item.source_index),
        )

    def _pick_latest_audio_file(self, recording_files: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

        for index, item in enumerate(recording_files):
            if not item.get("has_audio"):
                continue
            if not item.get("file_path"):
                continue

            ended_at = _parse_iso(item.get("recorded_ended_at"))
            started_at = _parse_iso(item.get("recorded_started_at"))
            end_offset = item.get("end_time_offset_ms")
            start_offset = item.get("start_time_offset_ms")

            sort_key = (
                ended_at or datetime.min,
                started_at or datetime.min,
                end_offset if end_offset is not None else -1,
                start_offset if start_offset is not None else -1,
                index,
            )
            candidates.append((sort_key, {**item, "_source_index": index}))

        if not candidates:
            return None
        return max(candidates, key=lambda item: item[0])[1]

    def _load_local_speech_segments(self, session: dict[str, Any]) -> list[dict[str, Any]]:
        speech_analysis = session.get("speech_analysis", {})
        segments = speech_analysis.get("segments") or []
        if isinstance(segments, list) and segments:
            return [item for item in segments if isinstance(item, dict)]

        segments_path = speech_analysis.get("segments_path")
        if not segments_path:
            return []

        absolute_path = self.recordings_dir / str(segments_path)
        if not absolute_path.exists():
            return []

        try:
            payload = json.loads(absolute_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        file_segments = payload.get("segments") or []
        if not isinstance(file_segments, list):
            return []
        return [item for item in file_segments if isinstance(item, dict)]

    def _build_transcript_windows(self, speech_segments: list[dict[str, Any]]) -> list[TranscriptWindow]:
        windows_by_participant: dict[str, list[TranscriptWindow]] = {}
        sorted_segments = sorted(
            speech_segments,
            key=lambda item: (
                float(item.get("start_sec", 0.0)),
                float(item.get("end_sec", 0.0)),
                int(item.get("segment_id") or 0),
            ),
        )

        for fallback_index, segment in enumerate(sorted_segments, start=1):
            start_sec = round(float(segment.get("start_sec", 0.0)), 4)
            end_sec = round(float(segment.get("end_sec", 0.0)), 4)
            if end_sec <= start_sec:
                continue

            segment_id = int(segment.get("segment_id") or fallback_index)
            participants = segment.get("participants") or []
            if not participants and segment.get("participant_id"):
                participants = [
                    {
                        "participant_id": segment.get("participant_id"),
                        "display_name": segment.get("display_name") or segment.get("participant_id"),
                    }
                ]

            for participant in participants:
                participant_id = str(participant.get("participant_id") or "").strip()
                if not participant_id:
                    continue

                display_name = (
                    str(participant.get("display_name") or segment.get("display_name") or participant_id).strip()
                    or participant_id
                )
                participant_windows = windows_by_participant.setdefault(participant_id, [])
                if participant_windows:
                    previous = participant_windows[-1]
                    if start_sec - previous.end_sec <= LOCAL_SEGMENT_MERGE_GAP_SEC:
                        previous.end_sec = round(max(previous.end_sec, end_sec), 4)
                        previous.source_segment_ids.append(segment_id)
                        continue

                participant_windows.append(
                    TranscriptWindow(
                        participant_id=participant_id,
                        display_name=display_name,
                        start_sec=start_sec,
                        end_sec=end_sec,
                        source_segment_ids=[segment_id],
                    )
                )

        windows: list[TranscriptWindow] = []
        for participant_windows in windows_by_participant.values():
            windows.extend(participant_windows)

        return sorted(
            windows,
            key=lambda item: (item.start_sec, item.end_sec, item.display_name.casefold()),
        )

    def _build_transcript_from_local_timeline(
        self,
        sources: list[ParticipantAudioSource],
        speech_segments: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], str]:
        source_by_participant = {item.participant_id: item for item in sources}
        windows = self._build_transcript_windows(speech_segments)
        transcript_segments: list[dict[str, Any]] = []

        for window in windows:
            source = source_by_participant.get(window.participant_id)
            if source is None:
                continue

            clip_start_sec = round(max(0.0, window.start_sec - source.start_offset_sec), 4)
            clip_end_sec = round(max(0.0, window.end_sec - source.start_offset_sec), 4)
            if clip_end_sec <= clip_start_sec:
                continue

            text = transcribe_audio_clip_text(
                str(source.absolute_path),
                start_sec=clip_start_sec,
                end_sec=clip_end_sec,
                language="tr",
                pad_start_sec=LOCAL_TRANSCRIPTION_CLIP_PAD_SEC,
                pad_end_sec=LOCAL_TRANSCRIPTION_CLIP_PAD_SEC,
            ).strip()
            if not text:
                continue

            transcript_segments.append(
                {
                    "speaker": window.display_name,
                    "participant_id": window.participant_id,
                    "start": round(window.start_sec, 4),
                    "end": round(window.end_sec, 4),
                    "text": text,
                    "source_segment_ids": window.source_segment_ids,
                }
            )

        transcript_segments.sort(
            key=lambda item: (float(item.get("start", 0.0)), str(item.get("speaker", "")))
        )
        return transcript_segments, self._build_full_text(transcript_segments)

    def _build_transcript_from_sources(
        self,
        sources: list[ParticipantAudioSource],
    ) -> tuple[list[dict[str, Any]], str]:
        segments: list[dict[str, Any]] = []

        for source in sources:
            items = transcribe_audio_segments(
                str(source.absolute_path),
                language="tr",
                speaker=source.display_name,
                participant_id=source.participant_id,
                offset_sec=source.start_offset_sec,
            )
            segments.extend(items)

        segments.sort(key=lambda item: (float(item.get("start", 0.0)), str(item.get("speaker", ""))))
        transcript = self._build_full_text(segments)
        return segments, transcript

    def _build_transcript(
        self,
        session: dict[str, Any],
        sources: list[ParticipantAudioSource],
    ) -> tuple[list[dict[str, Any]], str]:
        local_speech_segments = self._load_local_speech_segments(session)
        if local_speech_segments:
            timeline_segments, timeline_text = self._build_transcript_from_local_timeline(
                sources,
                local_speech_segments,
            )
            return timeline_segments, timeline_text
        return self._build_transcript_from_sources(sources)

    def _build_full_text(self, segments: list[dict[str, Any]]) -> str:
        lines: list[str] = []

        for segment in segments:
            text = str(segment.get("text") or "").strip()
            if not text:
                continue
            start_label = self._format_timestamp(float(segment.get("start", 0.0)))
            end_label = self._format_timestamp(float(segment.get("end", 0.0)))
            speaker = str(segment.get("speaker") or "Bilinmeyen")
            lines.append(f"[{speaker} | {start_label} - {end_label}]\n{text}\n")

        return "\n".join(lines).strip()

    def _summarize_meeting(self, transcript: str, segments: list[dict[str, Any]]) -> dict[str, Any]:
        if not transcript.strip():
            return {
                "executiveSummary": "",
                "keyDecisions": [],
                "topics": [],
            }

        result = self._llm().complete_json(
            system_prompt=SUMMARY_SYSTEM_PROMPT,
            user_prompt=json.dumps(
                {
                    "segments": segments[:120],
                    "transcript": transcript[:12000],
                },
                ensure_ascii=False,
                indent=2,
            ),
            temperature=0.1,
        )

        executive_summary = str(
            result.get("executiveSummary")
            or result.get("highlights_summary")
            or ""
        ).strip()

        key_decisions = result.get("keyDecisions")
        if not isinstance(key_decisions, list):
            minutes = result.get("hierarchical_minutes") or {}
            key_decisions = minutes.get("decisions", [])

        topics = result.get("topics")
        if not isinstance(topics, list):
            minutes = result.get("hierarchical_minutes") or {}
            topics = minutes.get("topics", [])

        return {
            "executiveSummary": _normalize_summary_text(executive_summary),
            "keyDecisions": _normalize_string_list(
                key_decisions,
                limit=MAX_DECISIONS,
            ),
            "topics": _normalize_string_list(
                topics,
                limit=MAX_TOPICS,
                max_item_length=80,
            ),
        }

    def _extract_tasks(
        self,
        transcript: str,
        segments: list[dict[str, Any]],
        *,
        meeting_date: str,
    ) -> list[dict[str, Any]]:
        if not transcript.strip():
            return []

        result = self._llm().complete_json(
            system_prompt=ACTION_ITEM_SYSTEM_PROMPT,
            user_prompt=json.dumps(
                {
                    "meeting_date": meeting_date,
                    "segments": segments[:120],
                    "transcript": transcript[:12000],
                },
                ensure_ascii=False,
                indent=2,
            ),
            temperature=0.1,
        )

        tasks: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()

        for item in result.get("action_items", []):
            if not isinstance(item, dict):
                continue

            confidence = _normalize_confidence(item.get("confidence", 0.0))
            normalized = {
                "task": _normalize_text(item.get("task", "")),
                "assignee": _normalize_text(item.get("assignee", ""), max_length=80),
                "due_date": _normalize_due_date(str(item.get("due_date", "")).strip()),
                "priority": _normalize_priority(item.get("priority", "")),
                "confidence": confidence,
                "type": _normalize_action_item_type(item.get("type", "")),
            }

            if not normalized["task"]:
                continue

            dedupe_key = (
                normalized["task"].casefold(),
                normalized["assignee"].casefold(),
                normalized["due_date"],
            )
            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            normalized["needs_review"] = _should_mark_for_review(item, confidence)
            tasks.append(normalized)

        return tasks

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

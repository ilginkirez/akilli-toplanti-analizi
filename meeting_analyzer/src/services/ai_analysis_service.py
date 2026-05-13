import json
import logging
import os
import hashlib
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
    transcribe_audio_segments,
)
from .meeting_store import meeting_store
from .notification_service import notify_assignees
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

            meeting_participants = self._collect_meeting_participants(
                session_id, session
            )
            graph_state = self._run_analysis_graph(
                session_id=session_id,
                session=session,
                sources=sources,
                meeting_date=self._resolve_meeting_date(session),
                meeting_participants=meeting_participants,
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
                "notifications_sent": graph_state.get("notifications_sent") or [],
                "notification_status": graph_state.get("notification_status"),
                "notification_error": graph_state.get("notification_error"),
                "notification_fingerprint": graph_state.get("notification_fingerprint"),
                "error": None,
                "completed": [
                    "transcription_agent",
                    "summary_agent",
                    "action_item_agent",
                    "finalize_analysis",
                    "notification_agent",
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
        meeting_participants: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return self.analysis_graph.invoke(
            {
                "session_id": session_id,
                "session": session,
                "sources": sources,
                "meeting_date": meeting_date,
                "meeting_participants": meeting_participants or [],
            }
        )

    def _collect_meeting_participants(
        self,
        session_id: str,
        session: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Meeting ve session verilerinden katilimci listesi olusturur (user_id, name, email)."""
        participants: list[dict[str, Any]] = []
        seen_user_ids: set[str] = set()
        seen_emails: set[str] = set()

        # Oncelikle meeting_store'dan katilimcilari al (user_id + email mevcut)
        meeting_id = session.get("meeting_id")
        if meeting_id:
            meeting = meeting_store.get_meeting(meeting_id)
            if meeting:
                # Organizer'i ekle
                organizer = meeting.get("organizer", {})
                org_name = organizer.get("name", "").strip()
                org_email = organizer.get("email", "").strip()
                if org_name and org_email:
                    org_user_id = self._find_user_id_for_email(
                        org_email, meeting.get("participants", [])
                    )
                    # meeting_participants'ta user_id yoksa user_store'dan ara
                    if not org_user_id:
                        org_user_id = self._lookup_user_id_by_email(org_email)
                    if org_user_id:
                        participants.append({
                            "user_id": org_user_id,
                            "name": org_name,
                            "email": org_email,
                        })
                        seen_user_ids.add(org_user_id)
                        seen_emails.add(org_email.lower())

                # Meeting katilimcilarini ekle
                for mp in meeting.get("participants", []):
                    user_id = mp.get("user_id")
                    name = mp.get("name", "").strip()
                    email = mp.get("email", "").strip()
                    # user_id yoksa user_store'dan email ile ara
                    if not user_id and email:
                        user_id = self._lookup_user_id_by_email(email)
                    if not user_id or not name:
                        continue
                    if user_id in seen_user_ids:
                        continue
                    if email.lower() in seen_emails:
                        continue
                    participants.append({
                        "user_id": user_id,
                        "name": name,
                        "email": email,
                    })
                    seen_user_ids.add(user_id)
                    if email:
                        seen_emails.add(email.lower())

        logger.debug(
            "[session_id=%s] Meeting katilimcilari toplandi: %d kisi",
            session_id,
            len(participants),
        )
        return participants

    @staticmethod
    def _find_user_id_for_email(
        email: str,
        participants: list[dict[str, Any]],
    ) -> str | None:
        """Verilen email adresine sahip katilimcinin user_id'sini bulur."""
        email_lower = email.strip().lower()
        for p in participants:
            if (p.get("email") or "").strip().lower() == email_lower:
                uid = p.get("user_id")
                if uid:
                    return uid
        return None

    @staticmethod
    def _lookup_user_id_by_email(email: str) -> str | None:
        """user_store'dan email ile user_id arar (fallback)."""
        try:
            from .user_store import user_store
            with user_store._lock, user_store._connect() as conn:
                row = conn.execute(
                    "SELECT id FROM users WHERE email = ? AND status = 'active'",
                    (email.strip().lower(),),
                ).fetchone()
                if row:
                    return row["id"]
        except Exception:
            logger.debug("user_store email lookup basarisiz: email=%s", email)
        return None

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

    def _collect_sources(self, session: dict[str, Any]) -> list[ParticipantAudioSource]:
        """Ses analizi icin katilimci kayit dosyalarini toplar."""
        sources: list[ParticipantAudioSource] = []
        index = 0
        for participant in session.get("participants", []):
            if is_system_participant(participant):
                continue
            participant_id = participant.get("participant_id")
            if not participant_id:
                continue

            display_name = participant.get("display_name") or participant_id
            for item in participant.get("recording_files", []):
                if not item.get("has_audio"):
                    continue
                relative_path = item.get("file_path")
                if not relative_path:
                    continue
                absolute_path = self.recordings_dir / relative_path
                if not absolute_path.exists():
                    logger.warning(
                        "[AI] Kayit dosyasi bulunamadi, atlanacak: %s",
                        absolute_path,
                    )
                    continue

                start_offset_sec = float(item.get("start_time_offset_ms") or 0) / 1000.0
                sources.append(
                    ParticipantAudioSource(
                        participant_id=participant_id,
                        display_name=display_name,
                        absolute_path=absolute_path,
                        relative_path=relative_path,
                        start_offset_sec=start_offset_sec,
                        source_index=index,
                    )
                )
                index += 1
        return sources

    def _build_transcript(
        self,
        session: dict[str, Any],
        sources: list[ParticipantAudioSource],
    ) -> tuple[list[dict[str, Any]], str]:
        """Her katilimcinin ses dosyasini transkripte eder ve birlestirir."""
        all_items: list[dict[str, Any]] = []
        for source in sources:
            try:
                items = transcribe_audio_segments(
                    str(source.absolute_path),
                    speaker=source.display_name,
                    participant_id=source.participant_id,
                    offset_sec=source.start_offset_sec,
                )
                all_items.extend(items)
                logger.info(
                    "[session=%s] Transkripsiyon tamamlandi: participant=%s segment=%d",
                    session.get("session_id", "?"),
                    source.display_name,
                    len(items),
                )
            except Exception as exc:
                logger.warning(
                    "[session=%s] Transkripsiyon basarisiz: participant=%s hata=%s",
                    session.get("session_id", "?"),
                    source.display_name,
                    exc,
                )

        # Zamana gore sirala
        all_items.sort(key=lambda x: float(x.get("start") or 0.0))

        lines = []
        for item in all_items:
            speaker = item.get("speaker", "")
            text = item.get("text", "")
            if speaker and text:
                lines.append(f"[{speaker}]: {text}")
        full_text = "\n".join(lines)
        return all_items, full_text

    def _notify_action_items(
        self,
        *,
        session_id: str,
        action_items: list[dict[str, Any]],
        meeting_participants: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not action_items:
            return {
                "notifications_sent": [],
                "notification_status": "skipped",
                "notification_error": None,
                "notification_fingerprint": None,
            }

        fingerprint = self._notification_fingerprint(
            action_items=action_items,
            meeting_participants=meeting_participants,
        )
        existing_analysis = session_store.load_session(session_id).get("ai_analysis", {})
        existing_notifications = existing_analysis.get("notifications_sent") or []
        if (
            fingerprint
            and existing_analysis.get("notification_fingerprint") == fingerprint
            and existing_notifications
        ):
            logger.info(
                "[session_id=%s] Bildirimler tekrar gonderilmedi; ayni fingerprint daha once islenmis.",
                session_id,
            )
            return {
                "notifications_sent": existing_notifications,
                "notification_status": "skipped_duplicate",
                "notification_error": None,
                "notification_fingerprint": fingerprint,
            }

        try:
            dashboard_url = os.getenv("DASHBOARD_URL", "").strip().rstrip("/")
            meeting = meeting_store.get_by_session_id(session_id)
            if dashboard_url and meeting:
                dashboard_url = f"{dashboard_url}/meetings/{meeting['id']}"
            else:
                dashboard_url = None

            notifications_sent = notify_assignees(
                action_items=action_items,
                meeting_participants=meeting_participants,
                dashboard_url=dashboard_url,
            )
            return {
                "notifications_sent": notifications_sent,
                "notification_status": "sent" if notifications_sent else "skipped",
                "notification_error": None,
                "notification_fingerprint": fingerprint,
            }
        except Exception as exc:
            logger.warning(
                "[session_id=%s] Gorev bildirimi gonderilemedi, analiz sonucu etkilenmedi.",
                session_id,
                exc_info=True,
            )
            return {
                "notifications_sent": [],
                "notification_status": "failed",
                "notification_error": str(exc),
                "notification_fingerprint": fingerprint,
            }

    @staticmethod
    def _notification_fingerprint(
        *,
        action_items: list[dict[str, Any]],
        meeting_participants: list[dict[str, Any]],
    ) -> str | None:
        if not action_items:
            return None

        recipients = {
            str(item.get("user_id")): {
                "name": str(item.get("name") or "").strip(),
                "email": str(item.get("email") or "").strip().lower(),
            }
            for item in meeting_participants
            if item.get("user_id")
        }

        fingerprint_items: list[dict[str, Any]] = []
        for item in action_items:
            assignee_id = item.get("assigned_to_user_id")
            recipient = recipients.get(str(assignee_id), {}) if assignee_id else {}
            fingerprint_items.append(
                {
                    "task": str(item.get("task") or item.get("title") or "").strip(),
                    "assigned_to_user_id": assignee_id,
                    "due_date": str(item.get("due_date") or "").strip(),
                    "priority": str(item.get("priority") or "").strip(),
                    "needs_review": bool(item.get("needs_review", False)),
                    "ambiguous": bool(item.get("ambiguous", False)),
                    "recipient_email": recipient.get("email", ""),
                    "recipient_name": recipient.get("name", ""),
                }
            )

        fingerprint_items.sort(
            key=lambda item: (
                str(item.get("assigned_to_user_id") or ""),
                str(item.get("task") or ""),
                str(item.get("due_date") or ""),
            )
        )
        payload = json.dumps(fingerprint_items, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

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

from typing import Any, TypedDict

from ..ai_output_models import MeetingSummaryOutput


class MeetingAnalysisState(TypedDict, total=False):
    session_id: str
    session: dict[str, Any]
    sources: list[Any]
    meeting_date: str
    transcript_segments: list[dict[str, Any]]
    full_text: str
    summary_result: dict[str, Any]
    action_items: list[dict[str, Any]]
    summary_output: MeetingSummaryOutput

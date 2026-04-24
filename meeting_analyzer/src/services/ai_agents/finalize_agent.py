from ..ai_output_models import build_meeting_summary_output
from .state import MeetingAnalysisState


def run_finalize_agent(state: MeetingAnalysisState) -> MeetingAnalysisState:
    summary_result = state.get("summary_result") or {}
    return {
        "summary_output": build_meeting_summary_output(
            executive_summary=summary_result.get("executiveSummary", ""),
            key_decisions=summary_result.get("keyDecisions", []),
            action_items=state.get("action_items", []),
            topics=summary_result.get("topics", []),
        )
    }

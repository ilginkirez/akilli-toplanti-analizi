from .context import AnalysisAgentService
from .state import MeetingAnalysisState


def run_action_item_agent(
    service: AnalysisAgentService,
    state: MeetingAnalysisState,
) -> MeetingAnalysisState:
    return {
        "action_items": service._extract_tasks(
            state.get("full_text", ""),
            state.get("transcript_segments", []),
            meeting_date=state.get("meeting_date", ""),
        )
    }

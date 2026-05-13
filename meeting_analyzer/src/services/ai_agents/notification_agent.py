from .context import AnalysisAgentService
from .state import MeetingAnalysisState


def run_notification_agent(
    service: AnalysisAgentService,
    state: MeetingAnalysisState,
) -> MeetingAnalysisState:
    return service._notify_action_items(
        session_id=state["session_id"],
        action_items=state.get("action_items", []),
        meeting_participants=state.get("meeting_participants", []),
    )

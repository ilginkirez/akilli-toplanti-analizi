from .context import AnalysisAgentService
from .state import MeetingAnalysisState


def run_summary_agent(
    service: AnalysisAgentService,
    state: MeetingAnalysisState,
) -> MeetingAnalysisState:
    return {
        "summary_result": service._summarize_meeting(
            state.get("full_text", ""),
            state.get("transcript_segments", []),
        )
    }

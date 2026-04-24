from .context import AnalysisAgentService
from .state import MeetingAnalysisState


def run_transcription_agent(
    service: AnalysisAgentService,
    state: MeetingAnalysisState,
) -> MeetingAnalysisState:
    transcript_segments, full_text = service._build_transcript(
        state["session"],
        state["sources"],
    )
    return {
        "transcript_segments": transcript_segments,
        "full_text": full_text,
    }

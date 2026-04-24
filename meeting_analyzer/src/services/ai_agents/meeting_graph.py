from langgraph.graph import END, START, StateGraph

from .action_item_agent import run_action_item_agent
from .context import AnalysisAgentService
from .finalize_agent import run_finalize_agent
from .state import MeetingAnalysisState
from .summary_agent import run_summary_agent
from .transcription_agent import run_transcription_agent


def build_meeting_analysis_graph(service: AnalysisAgentService):
    graph = StateGraph(MeetingAnalysisState)
    graph.add_node(
        "transcription_agent",
        lambda state: run_transcription_agent(service, state),
    )
    graph.add_node(
        "summary_agent",
        lambda state: run_summary_agent(service, state),
    )
    graph.add_node(
        "action_item_agent",
        lambda state: run_action_item_agent(service, state),
    )
    graph.add_node("finalize_analysis", run_finalize_agent)
    graph.add_edge(START, "transcription_agent")
    graph.add_edge("transcription_agent", "summary_agent")
    graph.add_edge("summary_agent", "action_item_agent")
    graph.add_edge("action_item_agent", "finalize_analysis")
    graph.add_edge("finalize_analysis", END)
    return graph.compile()

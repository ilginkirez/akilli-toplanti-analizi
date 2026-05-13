from typing import Any, Protocol


class AnalysisAgentService(Protocol):
    def _build_transcript(
        self,
        session: dict[str, Any],
        sources: list[Any],
    ) -> tuple[list[dict[str, Any]], str]: ...

    def _notify_action_items(
        self,
        *,
        session_id: str,
        action_items: list[dict[str, Any]],
        meeting_participants: list[dict[str, Any]],
    ) -> dict[str, Any]: ...

    def _llm(self) -> Any: ...

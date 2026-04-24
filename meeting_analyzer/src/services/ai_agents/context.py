from typing import Any, Protocol


class AnalysisAgentService(Protocol):
    def _build_transcript(
        self,
        session: dict[str, Any],
        sources: list[Any],
    ) -> tuple[list[dict[str, Any]], str]: ...

    def _llm(self) -> Any: ...


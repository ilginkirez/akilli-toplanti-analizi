from typing import Any, Protocol


class AnalysisAgentService(Protocol):
    def _build_transcript(
        self,
        session: dict[str, Any],
        sources: list[Any],
    ) -> tuple[list[dict[str, Any]], str]: ...

    def _summarize_meeting(
        self,
        transcript: str,
        segments: list[dict[str, Any]],
    ) -> dict[str, Any]: ...

    def _extract_tasks(
        self,
        transcript: str,
        segments: list[dict[str, Any]],
        *,
        meeting_date: str,
    ) -> list[dict[str, Any]]: ...

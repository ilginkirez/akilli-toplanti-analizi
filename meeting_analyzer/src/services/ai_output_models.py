import re
from typing import Any, Literal

from pydantic import BaseModel, Field


class SummaryActionItem(BaseModel):
    id: str
    title: str
    description: str | None = None
    assignee_id: str | None = None
    due_date: str | None = None
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    needs_review: bool = False


class MeetingSummaryOutput(BaseModel):
    executiveSummary: str = ""
    keyDecisions: list[str] = Field(default_factory=list)
    actionItems: list[SummaryActionItem] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)

    @classmethod
    def empty(cls) -> "MeetingSummaryOutput":
        return cls()


def build_meeting_summary_output(
    *,
    executive_summary: str,
    key_decisions: list[str] | None = None,
    action_items: list[dict[str, Any]] | None = None,
    topics: list[str] | None = None,
) -> MeetingSummaryOutput:
    return MeetingSummaryOutput(
        executiveSummary=" ".join(str(executive_summary or "").strip().split()),
        keyDecisions=_normalize_strings(key_decisions or []),
        actionItems=_build_action_items(action_items or []),
        topics=_normalize_strings(topics or []),
    )


def _build_action_items(items: list[dict[str, Any]]) -> list[SummaryActionItem]:
    normalized: list[SummaryActionItem] = []

    for index, item in enumerate(items, start=1):
        title = _normalize_text(item.get("title") or item.get("task"), max_length=200)
        if not title:
            continue

        assignee = _normalize_text(
            item.get("assignee_id") or item.get("assignee"),
            max_length=80,
        )
        description = _normalize_text(item.get("description"), max_length=500) or None
        due_date = _normalize_text(item.get("due_date"), max_length=32) or None

        normalized.append(
            SummaryActionItem(
                id=_build_action_item_id(index, title),
                title=title,
                description=description,
                assignee_id=_build_assignee_id(assignee),
                due_date=due_date,
                priority=_map_priority(item.get("priority")),
                needs_review=bool(item.get("needs_review", False)),
            )
        )

    return normalized


def _normalize_strings(items: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for item in items:
        text = _normalize_text(item, max_length=120)
        if not text:
            continue

        key = text.casefold()
        if key in seen:
            continue

        seen.add(key)
        normalized.append(text)

    return normalized


def _normalize_text(value: Any, max_length: int) -> str:
    text = " ".join(str(value or "").strip().split())
    return text[:max_length].strip(" ,;:-")


def _build_action_item_id(index: int, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
    if not slug:
        slug = "item"
    return f"action-item-{index}-{slug[:40]}"


def _build_assignee_id(assignee: str) -> str | None:
    if not assignee:
        return None

    slug = re.sub(r"[^a-z0-9]+", "-", assignee.casefold()).strip("-")
    if not slug:
        return None
    return f"person-{slug[:40]}"


def _map_priority(value: Any) -> Literal["low", "medium", "high", "urgent"]:
    priority = str(value or "").strip().lower()
    if priority == "critical":
        return "urgent"
    if priority in {"low", "medium", "high", "urgent"}:
        return priority
    return "medium"

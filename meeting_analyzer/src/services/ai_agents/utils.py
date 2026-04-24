from datetime import datetime
from typing import Any

VALID_PRIORITIES = {"", "low", "medium", "high", "critical"}
VALID_ACTION_ITEM_TYPES = {"direct", "volunteer", "implicit", "conditional", "group"}
MAX_TOPICS = 5
MAX_DECISIONS = 5

def normalize_summary_text(value: Any, max_length: int = 1000) -> str:
    return " ".join(str(value or "").strip().split())[:max_length].strip()


def normalize_string_list(
    items: Any,
    *,
    limit: int,
    max_item_length: int = 120,
) -> list[str]:
    if not isinstance(items, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()

    for item in items:
        text = " ".join(str(item).strip().split())
        if not text:
            continue

        text = text[:max_item_length].strip(" ,;:-")
        if not text:
            continue

        key = text.casefold()
        if key in seen:
            continue

        seen.add(key)
        normalized.append(text)
        if len(normalized) >= limit:
            break

    return normalized


def normalize_due_date(value: str) -> str:
    if not value:
        return ""

    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def normalize_priority(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in VALID_PRIORITIES else ""


def normalize_action_item_type(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in VALID_ACTION_ITEM_TYPES:
        return normalized
    return "implicit"


def normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return round(max(0.0, min(1.0, confidence)), 2)


def normalize_text(value: Any, max_length: int = 240) -> str:
    return " ".join(str(value or "").strip().split())[:max_length].strip(" ,;:-")


def should_mark_for_review(item: dict[str, Any], confidence: float) -> bool:
    if confidence < 0.65:
        return True
    return bool(item.get("needs_review", False))

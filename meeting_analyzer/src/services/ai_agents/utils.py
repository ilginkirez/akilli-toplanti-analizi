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


def normalize_user_id(value: Any, valid_user_ids: set[str]) -> str | None:
    """Dönen user_id'nin gerçekten katılımcı listesinde olup olmadığını kontrol eder."""
    if not value:
        return None
    uid = str(value).strip()
    if uid in valid_user_ids:
        return uid
    return None


def normalize_candidates(value: Any, valid_user_ids: set[str]) -> list[str]:
    """Candidate listesindeki geçersiz user_id'leri filtreler."""
    if not isinstance(value, list):
        return []
    return [
        str(uid).strip()
        for uid in value
        if str(uid).strip() in valid_user_ids
    ]


# ─── Smart Dedup ─────────────────────────────────────────────────────────────

def _tokenize(text: str) -> set[str]:
    """Metni küçük harfli kelimelere ayırır (stop-word filtresiz)."""
    return {w for w in text.casefold().split() if len(w) > 1}


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """İki metin arasındaki Jaccard benzerliğini hesaplar (0.0–1.0)."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


DEDUP_SIMILARITY_THRESHOLD = 0.60


def deduplicate_tasks(
    tasks: list[dict[str, Any]],
    *,
    similarity_threshold: float = DEDUP_SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """
    Görev listesini akıllı dedup ile filtreler.
    - Aynı kişiye atanan + %70+ kelime benzerliği olan görevlerden
      daha yüksek confidence'lı olanı tutulur.
    - Farklı kişilere atanan aynı görevler korunur.
    """
    result: list[dict[str, Any]] = []

    for task in tasks:
        task_text = task.get("task", "")
        task_user = task.get("assigned_to_user_id") or ""
        is_duplicate = False

        for existing in result:
            existing_text = existing.get("task", "")
            existing_user = existing.get("assigned_to_user_id") or ""

            # Farklı kişilere atanmışsa → duplicate değil
            if task_user != existing_user:
                continue

            similarity = jaccard_similarity(task_text, existing_text)
            if similarity >= similarity_threshold:
                # Daha yüksek confidence'lı olanı tut
                if task.get("confidence", 0) > existing.get("confidence", 0):
                    result[result.index(existing)] = task
                is_duplicate = True
                break

        if not is_duplicate:
            result.append(task)

    return result

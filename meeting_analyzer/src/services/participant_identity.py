from typing import Any, Mapping, Optional


SYSTEM_PARTICIPANT_PREFIXES = ("EG_",)


def _matches_system_prefix(value: Optional[str]) -> bool:
    if not value:
        return False

    normalized = value.strip().upper()
    return any(normalized.startswith(prefix) for prefix in SYSTEM_PARTICIPANT_PREFIXES)


def is_system_participant_id(participant_id: Optional[str]) -> bool:
    return _matches_system_prefix(participant_id)


def is_system_participant(participant: Mapping[str, Any]) -> bool:
    return any(
        _matches_system_prefix(candidate)
        for candidate in (
            participant.get("participant_id"),
            participant.get("display_name"),
            participant.get("name"),
        )
    )

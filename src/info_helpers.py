from __future__ import annotations

from typing import Dict, List, Optional

from challenge import Challenge
from forum_sync import state_display


DIFFICULTY_ORDER = {
    "welcome": 0,
    "beginner": 1,
    "easy": 2,
    "medium": 3,
    "hard": 4,
}

STATUS_ORDER = {
    "idea": 0,
    "playtest": 1,
    "done": 2,
    "scrapped": 3,
}


def difficulty_rank(value: Optional[str]) -> int:
    if not value:
        return 99
    return DIFFICULTY_ORDER.get(value.lower(), 50)


def status_rank(value: Optional[str]) -> int:
    if not value:
        return 99
    return STATUS_ORDER.get(value.lower(), 50)


def format_challenge_line(
    challenge: Challenge,
    thread_record: Optional[Dict[str, int]],
) -> str:
    if thread_record:
        thread_id = thread_record.get("thread_id")
        if thread_id:
            return f"<#{thread_id}>"
    return f"[{challenge.category}] {challenge.display_name}"


def sort_by_status_difficulty(challenges: List[Challenge]) -> List[Challenge]:
    return sorted(
        challenges,
        key=lambda c: (
            status_rank(c.status),
            difficulty_rank(c.difficulty),
            c.display_name.lower() if c.display_name else "",
        ),
    )


def group_challenges_by_status(challenges: List[Challenge]) -> Dict[str, List[Challenge]]:
    groups: Dict[str, List[Challenge]] = {}
    for challenge in challenges:
        status = challenge.status
        if status == "scrapped" or status is None:
            continue
        groups.setdefault(status, []).append(challenge)
    for status in list(groups.keys()):
        groups[status] = sort_by_status_difficulty(groups[status])
    return groups


def status_ordered_statuses(groups: Dict[str, List[Challenge]]) -> List[str]:
    ordered: List[str] = []
    for status, _ in sorted(STATUS_ORDER.items(), key=lambda item: item[1]):
        if status in groups:
            ordered.append(status)
    for status in sorted(groups.keys()):
        if status not in ordered and status != "scrapped":
            ordered.append(status)
    return ordered

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RecipeProposal:
    command: str
    explanation: str
    risk: str = "low"
    notes: list[str] = field(default_factory=list)


def match_recipe(request: str) -> RecipeProposal | None:
    return numbered_text_files(request)


def numbered_text_files(request: str) -> RecipeProposal | None:
    normalized = " ".join(request.lower().split())
    if not re.search(r"\b(make|create)\b", normalized):
        return None
    if not re.search(r"\b(new )?(files|txt files|text files)\b", normalized):
        return None
    if ".txt" not in normalized and "txt" not in normalized and "text" not in normalized:
        return None
    if not any(phrase in normalized for phrase in ("this folder", "current folder", "current directory", "here")):
        return None
    if not any(phrase in normalized for phrase in ("in each file", "each file", "inside each", "contents")):
        return None
    if not any(phrase in normalized for phrase in ("increasing number", "numbers", "numbered", "1 -")):
        return None

    count_match = re.search(r"\b(\d{1,4})\b", normalized)
    if not count_match:
        return None

    count = int(count_match.group(1))
    if count < 1 or count > 9999:
        return None

    width = max(2, len(str(count)))
    command = (
        f"for i in {{1..{count}}}; do "
        f"printf '%s\\n' \"$i\" > \"$(printf '%0{width}d.txt' \"$i\")\"; "
        "done"
    )
    return RecipeProposal(
        command=command,
        explanation=f"Creates {count} numbered .txt files in the current directory, with each file containing its number.",
        risk="low",
        notes=["Uses relative paths in the current directory."],
    )

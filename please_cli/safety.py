from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from enum import Enum


class SafetyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    REFUSE = "refuse"


@dataclass(frozen=True)
class SafetyAssessment:
    level: SafetyLevel
    reasons: tuple[str, ...] = ()
    confirmation_phrase: str | None = None

    @property
    def allowed(self) -> bool:
        return self.level is not SafetyLevel.REFUSE


REFUSAL_PATTERNS = (
    re.compile(r"\brm\s+-(?:[^\s]*r[^\s]*f|[^\s]*f[^\s]*r)\s+(?:--\s+)?/(?:\s|$)"),
    re.compile(r"\brm\s+-(?:[^\s]*r[^\s]*f|[^\s]*f[^\s]*r)\s+(?:--\s+)?/[\*]+(?:\s|$)"),
    re.compile(r"\brm\s+-(?:[^\s]*r[^\s]*f|[^\s]*f[^\s]*r)\s+~(?:\s|/|$)"),
    re.compile(r"\brm\s+-(?:[^\s]*r[^\s]*f|[^\s]*f[^\s]*r).*\$HOME"),
    re.compile(r"\bdd\s+.*\bof=/dev/(?:disk|rdisk)"),
    re.compile(r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;:"),
    re.compile(r"\bchmod\s+-R\s+777\s+/(?:\s|$)"),
    re.compile(r"\bchown\s+-R\s+[^ ]+\s+/(?:\s|$)"),
)

HIGH_RISK_COMMANDS = {
    "rm",
    "rmdir",
    "mv",
    "dd",
    "chmod",
    "chown",
    "diskutil",
    "mkfs",
    "brew",
    "pip",
    "pip3",
    "npm",
    "pnpm",
    "yarn",
}

DESTRUCTIVE_FLAGS = re.compile(r"\s-(?:[A-Za-z]*r[A-Za-z]*|[A-Za-z]*f[A-Za-z]*)\b")
SHELL_OPERATORS = ("|", ">", ">>", "&&", "||", ";")


def assess(command: str) -> SafetyAssessment:
    normalized = " ".join(command.strip().split())
    if not normalized:
        return SafetyAssessment(SafetyLevel.REFUSE, ("Empty command.",))

    for pattern in REFUSAL_PATTERNS:
        if pattern.search(normalized):
            return SafetyAssessment(
                SafetyLevel.REFUSE,
                ("Refusing an obviously catastrophic command.",),
            )

    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return SafetyAssessment(SafetyLevel.REFUSE, (f"Command could not be parsed: {exc}",))

    if not tokens:
        return SafetyAssessment(SafetyLevel.REFUSE, ("Empty command.",))

    reasons: list[str] = []
    first = tokens[0].split("/")[-1]

    if first == "sudo":
        reasons.append("Uses sudo.")
        first = tokens[1].split("/")[-1] if len(tokens) > 1 else first

    if first in HIGH_RISK_COMMANDS:
        reasons.append(f"Uses `{first}`, which can modify files or system state.")

    if DESTRUCTIVE_FLAGS.search(normalized):
        reasons.append("Includes recursive or force-style flags.")

    if re.search(r">\s*/dev/null|2>\s*/dev/null", normalized):
        reasons.append("Suppresses output, which can hide errors.")

    if re.search(r"\b(curl|wget)\b.*\|\s*(sh|bash|zsh)\b", normalized):
        reasons.append("Runs a downloaded script through a shell.")

    if any(part in normalized for part in (" /System", " /Library", " ~/Library")):
        reasons.append("Targets system or user library paths.")

    if reasons:
        return SafetyAssessment(SafetyLevel.HIGH, tuple(reasons), confirmation_phrase="DELETE")

    if any(op in normalized for op in SHELL_OPERATORS):
        return SafetyAssessment(SafetyLevel.MEDIUM, ("Uses shell operators.",))

    return SafetyAssessment(SafetyLevel.LOW)

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


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

FILE_MODIFYING_VERBS = {
    "rm",
    "rmdir",
    "mv",
    "cp",
    "chmod",
    "chown",
    "chgrp",
    "dd",
    "mkfs",
    "diskutil",
    "shred",
}

SYSTEM_COMMANDS = {
    "brew",
    "pip",
    "pip3",
    "npm",
    "pnpm",
    "yarn",
    "make",
    "cargo",
}

FILE_VERB_RE = re.compile(
    r"\b(?:rm|rmdir|mv|cp|chmod|chown|chgrp|dd|mkfs|diskutil|shred)\b"
)
MODERATE_SIGNAL_COMMANDS = {"kill", "pkill", "killall"}
FIND_ACTIONS_RE = re.compile(r"\bfind\b.*\s-(?:exec|execdir|delete)\b", flags=re.DOTALL)
SHELL_BODY_RE = re.compile(r"\b(?:bash|sh|zsh)\s+-c\s+(['\"])(.*?)\1", flags=re.DOTALL)
DESTRUCTIVE_FLAGS = re.compile(r"\s+-\S*[rf]\S*")
SHELL_OPERATORS = ("|", ">", ">>", "&&", "||", ";")
QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"")

HOME = Path.home()
_SEPARATORS = {"|", "||", "&&", ";", ">", ">>", "2>", "2>>"}
_ROOT_TARGETS = {"/", "/*", "/.", "/..", "/.*", "/.??*"}


def _expand_home(target: str) -> str:
    if target == "~":
        return str(HOME)
    if target.startswith("~/"):
        return str(HOME / target[2:])
    if target.startswith("$HOME"):
        return str(HOME / target[len("$HOME") :].lstrip("/"))
    if target.startswith("${HOME}"):
        return str(HOME / target[len("${HOME}") :].lstrip("/"))
    return target


def _target_is_catastrophic(target: str) -> bool:
    if target in _ROOT_TARGETS:
        return True
    if target.startswith(("~", "$HOME", "${HOME}")):
        expanded = _expand_home(target)
        try:
            path = Path(expanded).resolve()
        except OSError:
            path = Path(expanded).absolute()
        return path == HOME or HOME in path.parents
    if target.startswith("/"):
        try:
            path = Path(target).resolve()
        except OSError:
            path = Path(target).absolute()
        return path == HOME or HOME in path.parents
    return False


def _catastrophic_delete_reason(tokens: list[str]) -> str | None:
    """Refuse any recursive+force delete aimed at / or the user's home,
    regardless of how the flags or path are spelled (`rm -r -f`, `$HOME`,
    `~/x`, a literal /Users/... path, inside find -exec, ...)."""
    for idx, token in enumerate(tokens):
        base = token.split("/")[-1].strip("\"'")
        if base not in {"rm", "rmdir"}:
            continue
        recursive = force = False
        targets: list[str] = []
        j = idx + 1
        while j < len(tokens) and tokens[j] not in _SEPARATORS:
            candidate = tokens[j]
            if candidate == "--":
                j += 1
                continue
            if candidate.startswith("-"):
                letters = candidate.lstrip("-")
                recursive = recursive or "r" in letters
                force = force or "f" in letters
            else:
                targets.append(candidate)
            j += 1
        if recursive and force and any(_target_is_catastrophic(t) for t in targets):
            return "Refusing a recursive force-delete aimed at your home directory or root."
    return None


def file_verbs(command: str) -> list[str]:
    """Destructive file verbs outside of quoted strings, plus inside `sh -c` bodies."""
    results = set(FILE_VERB_RE.findall(QUOTED_RE.sub(" ", command)))
    for _, body in SHELL_BODY_RE.findall(command):
        results.update(FILE_VERB_RE.findall(body))
    return sorted(results)


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

    if reason := _catastrophic_delete_reason(tokens):
        return SafetyAssessment(SafetyLevel.REFUSE, (reason,))

    reasons: list[str] = []
    seen: set[str] = set()

    def add(reason: str) -> None:
        if reason not in seen:
            seen.add(reason)
            reasons.append(reason)

    first = tokens[0].split("/")[-1]

    if first == "sudo":
        add("Uses sudo.")
        first = tokens[1].split("/")[-1] if len(tokens) > 1 else first

    if first in SYSTEM_COMMANDS:
        add(f"Uses `{first}`, which modifies packages or system state.")

    for verb in file_verbs(normalized):
        add(f"Uses `{verb}`, which can modify or remove files.")

    if first in FILE_MODIFYING_VERBS and DESTRUCTIVE_FLAGS.search(normalized):
        add("Includes recursive or force-style flags.")

    if FIND_ACTIONS_RE.search(normalized):
        add("Runs a subcommand or deletes files via `find` (`-exec`/`-delete`).")

    if re.search(r">\s*/dev/null|2>\s*/dev/null", normalized):
        add("Suppresses output, which can hide errors.")

    if re.search(r"\b(curl|wget)\b.*\|\s*(sh|bash|zsh)\b", normalized):
        add("Runs a downloaded script through a shell.")

    if any(part in normalized for part in (" /System", " /Library", " ~/Library")):
        add("Targets system or user library paths.")

    if reasons:
        return SafetyAssessment(SafetyLevel.HIGH, tuple(reasons), confirmation_phrase="DELETE")

    if first in MODERATE_SIGNAL_COMMANDS:
        return SafetyAssessment(SafetyLevel.MEDIUM, (f"Signals processes via `{first}`.",))

    if any(op in normalized for op in SHELL_OPERATORS):
        return SafetyAssessment(SafetyLevel.MEDIUM, ("Uses shell operators.",))

    return SafetyAssessment(SafetyLevel.LOW)

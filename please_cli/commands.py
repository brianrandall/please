from __future__ import annotations

import re
import shlex


def normalize_command(command: str, cwd: str) -> str:
    """Fix common model output issues before safety/execution."""
    command = quote_raw_cwd(command, cwd)
    command = add_missing_printf_loop_value(command)
    return command


def quote_raw_cwd(command: str, cwd: str) -> str:
    if not cwd or cwd not in command:
        return command

    if f"'{cwd}'" in command or f'"{cwd}"' in command:
        return command

    quoted = shlex.quote(cwd)
    if quoted == cwd:
        return command

    return command.replace(cwd, quoted)


def add_missing_printf_loop_value(command: str) -> str:
    if not re.search(r"\bfor\s+i\s+in\b.*\bdone\b", command, flags=re.DOTALL):
        return command

    pattern = re.compile(r"(printf\s+(['\"])%[0-9]*d(?:\\n|\n)?\2)\s*(?=>)", flags=re.DOTALL)
    return pattern.sub(r'\1 "$i" ', command)

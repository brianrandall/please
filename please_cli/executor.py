from __future__ import annotations

import subprocess


def shell_syntax_is_valid(command: str) -> tuple[bool, str]:
    """Returns (True, "") if the command parses under zsh, else (False, stderr)."""
    result = subprocess.run(
        ["/bin/zsh", "-n", "-c", command],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return True, ""
    return False, result.stderr.strip()


def run_command(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        shell=True,
        executable="/bin/zsh",
        text=True,
        capture_output=True,
        check=False,
    )

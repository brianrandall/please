from __future__ import annotations

import subprocess


def run_command(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        shell=True,
        executable="/bin/zsh",
        text=True,
        capture_output=True,
        check=False,
    )

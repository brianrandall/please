from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path.home() / ".config" / "please" / "config.yaml"


@dataclass(frozen=True)
class Config:
    model: str = "qwen3:8b"
    fallback_model: str | None = "llama3.2:latest"
    ollama_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 120.0


def load_config(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        return Config()

    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        return Config()

    fallback = data.get("fallback_model")
    return Config(
        model=str(data.get("default_model") or data.get("model") or Config.model),
        fallback_model=str(fallback) if fallback else None,
        ollama_url=str(data.get("ollama_url") or Config.ollama_url),
        timeout_seconds=float(data.get("timeout_seconds") or Config.timeout_seconds),
    )


def config_template() -> dict[str, Any]:
    return {
        "default_model": Config.model,
        "fallback_model": "llama3.2:latest",
        "ollama_url": Config.ollama_url,
        "timeout_seconds": Config.timeout_seconds,
    }

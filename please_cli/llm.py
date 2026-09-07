from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from .commands import normalize_command
from .config import Config
from .prompts import SYSTEM_PROMPT, command_prompt, explain_prompt
from .recipes import match_recipe


class CommandProposal(BaseModel):
    command: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    risk: str = Field(pattern="^(low|medium|high)$")
    notes: list[str] = Field(default_factory=list)


COMMAND_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "string"},
        "explanation": {"type": "string"},
        "risk": {"type": "string", "enum": ["low", "medium", "high"]},
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["command", "explanation", "risk", "notes"],
}


class OllamaError(RuntimeError):
    pass


class EmptyThinkingResponse(OllamaError):
    pass


class OllamaClient:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._client = httpx.Client(base_url=config.ollama_url, timeout=config.timeout_seconds)

    def propose_command(self, request: str, cwd: str) -> CommandProposal:
        if recipe := match_recipe(request):
            return CommandProposal.model_validate(recipe.__dict__)

        errors: list[str] = []
        models = [self.config.model]
        if self.config.fallback_model and self.config.fallback_model not in models:
            models.append(self.config.fallback_model)

        for model in models:
            payload = {
                "model": model,
                "think": False,
                "keep_alive": -1,
                "stream": False,
                "format": COMMAND_SCHEMA,
                "options": {"temperature": 0, "num_predict": 1200},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": command_prompt(request=request, cwd=cwd)},
                ],
            }
            try:
                content = self._chat(payload)
                data: Any = json.loads(content)
                proposal = CommandProposal.model_validate(data)
                proposal.command = normalize_command(proposal.command, cwd)
            except EmptyThinkingResponse as exc:
                errors.append(f"{model}: {exc}")
                continue
            except (json.JSONDecodeError, ValidationError):
                errors.append(f"{model}: returned invalid command JSON")
                continue
            return proposal

        raise OllamaError("; ".join(errors) or "No model returned a usable command.")

    def explain(self, command: str) -> str:
        payload = {
            "model": self.config.model,
            "think": False,
            "keep_alive": -1,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 1000},
            "messages": [
                {"role": "system", "content": "You explain zsh commands clearly and briefly."},
                {"role": "user", "content": explain_prompt(command)},
            ],
        }
        return self._chat(payload).strip()

    def available_models(self) -> list[str]:
        try:
            response = self._client.get("/api/tags")
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise OllamaError("Could not connect to Ollama. Start it with `ollama serve`.") from exc
        except httpx.TimeoutException as exc:
            raise OllamaError(
                f"Ollama did not respond within {self.config.timeout_seconds:g} seconds. "
                "The first request after loading a model can be slow; try again or use a smaller model."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaError(f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text}") from exc

        data = response.json()
        models = data.get("models", [])
        return sorted(model.get("name", "") for model in models if isinstance(model, dict) and model.get("name"))

    def model_is_available(self, model: str | None = None) -> bool:
        wanted = model or self.config.model
        return wanted in self.available_models()

    def model_is_loaded(self, model: str | None = None) -> bool:
        wanted = model or self.config.model
        try:
            response = self._client.get("/api/ps")
            response.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
            return False
        loaded = {
            entry.get("name")
            for entry in response.json().get("models", [])
            if isinstance(entry, dict) and entry.get("name")
        }
        return wanted in loaded

    def _chat(self, payload: dict[str, Any]) -> str:
        try:
            response = self._client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise OllamaError("Could not connect to Ollama. Start it with `ollama serve`.") from exc
        except httpx.TimeoutException as exc:
            raise OllamaError(
                f"Ollama did not respond within {self.config.timeout_seconds:g} seconds. "
                "The first request after loading a model can be slow; try again or use a smaller model."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaError(f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text}") from exc

        data = response.json()
        message = data.get("message", {})
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content

        if message.get("thinking") and data.get("done_reason") == "length":
            raise EmptyThinkingResponse("returned thinking text but no command")

        raise OllamaError(f"Ollama response did not include message content: {data}")

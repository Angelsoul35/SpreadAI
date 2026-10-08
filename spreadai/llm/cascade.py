"""A cascade of LLM clients with automatic fallback.

The cascade tries each provider in order. If one fails (no key, rate limit,
network error, bad response) it moves to the next. This is multi-LLM
orchestration: you get resilience (one provider down does not stop you) and
freedom to prefer a cheaper or local model first and fall back to a stronger
one only when needed.
"""

from __future__ import annotations

from .base import LLMClient, LLMError, LLMResult


class CascadeLLM:
    name = "cascade"

    def __init__(self, clients: list[LLMClient]) -> None:
        if not clients:
            raise ValueError("cascade needs at least one client")
        self.clients = clients

    @property
    def model(self) -> str:
        return "cascade[" + ",".join(c.name for c in self.clients) + "]"

    def complete(self, system, prompt, max_tokens=512, temperature=0.0) -> LLMResult:
        errors: list[str] = []
        for client in self.clients:
            try:
                return client.complete(system, prompt, max_tokens, temperature)
            except LLMError as exc:
                errors.append(str(exc))
        raise LLMError("all providers failed -> " + " | ".join(errors))

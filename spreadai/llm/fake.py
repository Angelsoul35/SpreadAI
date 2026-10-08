"""Test doubles for the LLM interface (no network)."""

from __future__ import annotations

from collections.abc import Callable

from .base import LLMError, LLMResult


class FakeLLM:
    """Returns a scripted reply. Used in tests so nothing hits a real API."""

    name = "fake"
    model = "fake-1"

    def __init__(self, reply: str | Callable[[str, str], str] = "ok") -> None:
        self._reply = reply

    def complete(self, system, prompt, max_tokens=512, temperature=0.0) -> LLMResult:
        text = self._reply(system, prompt) if callable(self._reply) else self._reply
        return LLMResult(text=text, provider=self.name, model=self.model)


class FailingLLM:
    """Always raises LLMError. Used to test cascade fallback."""

    def __init__(self, name: str = "broken") -> None:
        self.name = name
        self.model = f"{name}-0"

    def complete(self, system, prompt, max_tokens=512, temperature=0.0):
        raise LLMError(f"{self.name}: forced failure")

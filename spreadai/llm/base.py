"""A provider-agnostic LLM client interface.

Every provider (Anthropic, OpenAI, Gemini, DeepSeek, a local Ollama model, ...)
is wrapped as an :class:`LLMClient` with the same ``complete`` method. Code that
needs an LLM depends on this interface, not on any one vendor, so you can switch
providers or run several in a fallback cascade without touching the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class LLMError(Exception):
    """Raised when a provider call fails (network, bad status, or bad response)."""


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str


@runtime_checkable
class LLMClient(Protocol):
    name: str
    model: str

    def complete(
        self,
        system: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> LLMResult:
        """Return the model's text answer, or raise :class:`LLMError`."""
        ...

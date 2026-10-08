"""Build an LLM cascade from a provider spec like ``anthropic,openai,ollama``."""

from __future__ import annotations

from .base import LLMClient
from .cascade import CascadeLLM
from .providers import build_client

DEFAULT_SPEC = "anthropic,openai,gemini,deepseek,ollama"


def build_llm(spec: str = DEFAULT_SPEC) -> LLMClient:
    """Return a cascade over the named providers (comma-separated, in order).

    Each provider reads its own API key from the environment. A provider with no
    key does not fail at build time; it fails at call time, and the cascade falls
    back to the next one. A single provider name returns just that client.
    """
    names = [n.strip() for n in spec.split(",") if n.strip()]
    if not names:
        raise ValueError("empty provider spec")
    clients = [build_client(n) for n in names]
    if len(clients) == 1:
        return clients[0]
    return CascadeLLM(clients)

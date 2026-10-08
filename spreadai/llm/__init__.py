"""Provider-agnostic LLM layer: one interface, many providers, with fallback."""

from __future__ import annotations

from .base import LLMClient, LLMError, LLMResult
from .cascade import CascadeLLM
from .factory import DEFAULT_SPEC, build_llm

__all__ = ["LLMClient", "LLMError", "LLMResult", "CascadeLLM", "build_llm", "DEFAULT_SPEC"]

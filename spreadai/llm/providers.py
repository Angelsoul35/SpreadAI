"""HTTP adapters for several LLM providers, all behind one interface.

Each adapter talks to the provider's REST API with ``httpx`` and maps the
response to an :class:`LLMResult`. We use plain HTTP (not each vendor's SDK) so
the adapters are uniform and share one dependency. Any failure becomes an
:class:`LLMError`, which is what the cascade uses to fall back to the next
provider.

API keys come from the environment; nothing is hard-coded.
"""

from __future__ import annotations

import os

import httpx

from .base import LLMClient, LLMError, LLMResult

DEFAULT_TIMEOUT = 30.0


class AnthropicClient:
    """Anthropic Messages API."""

    name = "anthropic"

    def __init__(
        self,
        model: str = "claude-sonnet-5-5",
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com",
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.model = model
        self._key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._url = base_url.rstrip("/") + "/v1/messages"
        self._timeout = timeout

    def complete(self, system, prompt, max_tokens=512, temperature=0.0) -> LLMResult:
        if not self._key:
            raise LLMError("anthropic: ANTHROPIC_API_KEY is not set")
        try:
            resp = httpx.post(
                self._url,
                headers={
                    "x-api-key": self._key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            text = "".join(b.get("text", "") for b in data.get("content", []))
            return LLMResult(text=text, provider=self.name, model=self.model)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMError(f"anthropic: {exc}") from exc


class OpenAICompatibleClient:
    """OpenAI-style /chat/completions API. Also used for DeepSeek and others."""

    def __init__(
        self,
        name: str,
        model: str,
        api_key_env: str,
        base_url: str,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.name = name
        self.model = model
        self._key = api_key or os.getenv(api_key_env, "")
        self._key_env = api_key_env
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._timeout = timeout

    def complete(self, system, prompt, max_tokens=512, temperature=0.0) -> LLMResult:
        if not self._key:
            raise LLMError(f"{self.name}: {self._key_env} is not set")
        try:
            resp = httpx.post(
                self._url,
                headers={
                    "Authorization": f"Bearer {self._key}",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return LLMResult(text=text, provider=self.name, model=self.model)
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"{self.name}: {exc}") from exc


def OpenAIClient(model: str = "gpt-4o-mini", api_key: str | None = None) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        "openai", model, "OPENAI_API_KEY", "https://api.openai.com/v1", api_key
    )


def DeepSeekClient(
    model: str = "deepseek-chat", api_key: str | None = None
) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        "deepseek", model, "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1", api_key
    )


class GeminiClient:
    """Google Gemini generateContent API."""

    name = "gemini"

    def __init__(
        self,
        model: str = "gemini-1.5-flash",
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.model = model
        self._key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._timeout = timeout

    def complete(self, system, prompt, max_tokens=512, temperature=0.0) -> LLMResult:
        if not self._key:
            raise LLMError("gemini: GEMINI_API_KEY is not set")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self._key}"
        )
        try:
            resp = httpx.post(
                url,
                headers={"content-type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
            return LLMResult(text=text, provider=self.name, model=self.model)
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"gemini: {exc}") from exc


class OllamaClient:
    """Local open-source models served by Ollama (no API key, self-hosted)."""

    name = "ollama"

    def __init__(
        self, model: str = "llama3.1", base_url: str | None = None, timeout: float = DEFAULT_TIMEOUT
    ):
        self.model = model
        self._url = (base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self._timeout = timeout

    def complete(self, system, prompt, max_tokens=512, temperature=0.0) -> LLMResult:
        try:
            resp = httpx.post(
                self._url + "/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return LLMResult(text=data["message"]["content"], provider=self.name, model=self.model)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMError(f"ollama: {exc}") from exc


_FACTORIES = {
    "anthropic": lambda: AnthropicClient(),
    "openai": lambda: OpenAIClient(),
    "gemini": lambda: GeminiClient(),
    "deepseek": lambda: DeepSeekClient(),
    "ollama": lambda: OllamaClient(),
}


def build_client(name: str) -> LLMClient:
    name = name.strip().lower()
    if name not in _FACTORIES:
        raise ValueError(f"unknown provider: {name!r} (known: {', '.join(_FACTORIES)})")
    return _FACTORIES[name]()

# ADR-0004: Keep the LLM layer provider-agnostic

* Status: accepted
* Date: 2026-02-03

## Context

Parts of SpreadAI can use an LLM (the extractor fallback and the written memo). Tying the
code to one vendor is risky: prices change, a provider can be down, and some deployments
must run on a local model for data privacy.

## Decision

All LLM calls go through a small `LLMClient` interface with adapters for several providers
(Anthropic, OpenAI, Gemini, DeepSeek, local Ollama). A `CascadeLLM` tries them in order and
falls back on failure. The provider order is configuration.

## Consequences

* **Good:** no vendor lock-in; resilience (one provider down does not stop the system); you
  can prefer a cheap or local model first. The default memo mode needs no LLM at all.
* **Cost:** a shared, lowest-common-denominator interface, so provider-specific features are
  not exposed. For this use case that is fine.

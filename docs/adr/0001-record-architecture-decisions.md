# ADR-0001: Record architecture decisions

* Status: accepted
* Date: 2026-02-02

## Context

SpreadAI makes a few design choices that are not obvious (a confidence score, a human
review gate, a provider-agnostic LLM layer). A future reader needs the *why*.

## Decision

We keep short Architecture Decision Records in `docs/adr/`, one per important choice, each
with Context, Decision, and Consequences.

## Consequences

* Choices are easy to review later.
* The cost is one short Markdown file per decision.

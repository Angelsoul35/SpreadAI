# ADR-0003: Score confidence and route low-confidence cases to a human

* Status: accepted
* Date: 2026-02-03

## Context

An automatic spreader that always returns an answer is dangerous: a wrong spread used in a
credit decision can cost real money. The tool must know when it is not sure.

## Decision

Every spread gets a confidence score, built from field coverage and the validation checks.
When confidence is below a threshold (configurable) or the statement does not balance, the
result is flagged `needs_human_review`.

## Consequences

* **Good:** the tool is safe to use as a first pass. It speeds up the easy cases and hands
  the hard ones to a person.
* **Cost:** the threshold needs tuning per use case. Too high sends everything to review;
  too low lets errors through. It is a setting, not a fixed value.

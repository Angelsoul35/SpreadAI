# ADR-0002: Use the accounting identity as the main check

* Status: accepted
* Date: 2026-02-02

## Context

When you extract numbers from a document, some will be wrong: a missing line, a misread
digit, a label mapped to the wrong field. We need a cheap, strong signal that the
extraction is probably right.

## Decision

The main check is the accounting identity: total assets must equal total liabilities plus
equity, within a small tolerance. If it holds, the pieces are very likely consistent. If
it fails, something is wrong, so the confidence drops and the case goes to review.

## Consequences

* **Good:** one check catches most extraction errors, with no model and no labels beyond
  the numbers themselves.
* **Cost:** a statement that is itself wrong (bad source data) will fail the check even if
  the extraction was perfect. That is acceptable: either way, a human should look.

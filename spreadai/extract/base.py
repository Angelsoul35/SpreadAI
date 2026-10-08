"""Shared types and helpers for extraction."""

from __future__ import annotations

from dataclasses import dataclass, field

from spreadai.schema import BALANCE_SHEET_KEYS, INCOME_STATEMENT_KEYS, FinancialStatement

ALL_KEYS = BALANCE_SHEET_KEYS + INCOME_STATEMENT_KEYS


@dataclass
class ExtractionResult:
    statement: FinancialStatement
    method: str
    found_keys: list[str] = field(default_factory=list)

    @property
    def field_coverage(self) -> float:
        """Fraction of the canonical line items that were found."""
        return len(set(self.found_keys)) / len(ALL_KEYS)


def parse_amount(raw: str) -> float | None:
    """Parse a money string like ``1,234,567``, ``(1,234)`` or ``$ 1,000``."""
    s = raw.strip().replace("$", "").replace("COP", "").strip()
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace(",", "").replace(" ", "")
    try:
        value = float(s)
    except ValueError:
        return None
    return -value if negative else value

"""Parse a labelled financial statement from plain text.

This is the deterministic extractor. It reads lines of the form
``Label: amount``, maps each label to a canonical key (using the primary label
or any alias), and fills the statement. It also reads the company, period, and
currency. It needs no model, so it is fast and repeatable, and it handles clean
statements well. Messy statements fall back to the LLM extractor.
"""

from __future__ import annotations

from spreadai.labels import label_lookup
from spreadai.schema import (
    BALANCE_SHEET_KEYS,
    INCOME_STATEMENT_KEYS,
    BalanceSheet,
    FinancialStatement,
    IncomeStatement,
)

from .base import ExtractionResult, parse_amount

_LOOKUP = label_lookup()


def parse_text(text: str) -> ExtractionResult:
    company, period, currency = "Unknown", "Unknown", "COP"
    bs_values: dict[str, float] = {}
    is_values: dict[str, float] = {}
    found: list[str] = []

    for line in text.splitlines():
        if ":" not in line:
            continue
        label, _, value = line.rpartition(":")
        label = label.strip().lower()
        value = value.strip()

        if label == "company":
            company = value or company
            continue
        if label == "period":
            period = value or period
            continue
        if label == "currency":
            currency = value or currency
            continue

        key = _LOOKUP.get(label)
        if key is None:
            continue
        amount = parse_amount(value)
        if amount is None:
            continue
        if key in BALANCE_SHEET_KEYS:
            bs_values[key] = amount
            found.append(key)
        elif key in INCOME_STATEMENT_KEYS:
            is_values[key] = amount
            found.append(key)

    statement = FinancialStatement(
        company=company,
        period=period,
        currency=currency,
        balance_sheet=BalanceSheet(**bs_values),
        income_statement=IncomeStatement(**is_values),
    )
    return ExtractionResult(statement=statement, method="text", found_keys=found)

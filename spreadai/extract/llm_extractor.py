"""Extract a statement from messy text with an LLM (provider-agnostic cascade).

The deterministic parser handles clean statements. When a statement is messy
(odd labels, prose, a layout the parser does not recognise), this extractor asks
an LLM to return the canonical line items as JSON. It uses the same provider
cascade as the rest of the system, so it is not tied to any one vendor. In tests
we inject a fake client, so nothing hits a real API.
"""

from __future__ import annotations

import json

from spreadai.llm import LLMClient, build_llm
from spreadai.schema import (
    BALANCE_SHEET_KEYS,
    INCOME_STATEMENT_KEYS,
    BalanceSheet,
    FinancialStatement,
    IncomeStatement,
)

from .base import ExtractionResult

_ALL_KEYS = BALANCE_SHEET_KEYS + INCOME_STATEMENT_KEYS

_SYSTEM = (
    "You extract financial-statement line items. You return only a JSON object. "
    "Use these exact keys (missing items = 0): " + ", ".join(_ALL_KEYS) + ". "
    "Also include company, period, currency. Amounts are plain numbers."
)


class LLMExtractor:
    def __init__(self, llm: LLMClient | None = None, provider_spec: str | None = None) -> None:
        if llm is not None:
            self.llm = llm
        elif provider_spec:
            self.llm = build_llm(provider_spec)
        else:
            self.llm = build_llm()

    def extract(self, text: str) -> ExtractionResult:
        prompt = f"Extract the line items from this statement:\n\n{text}\n\nReturn only JSON."
        result = self.llm.complete(_SYSTEM, prompt, max_tokens=1024)
        data = _parse_json(result.text)

        bs_values = {k: float(data[k]) for k in BALANCE_SHEET_KEYS if _is_number(data.get(k))}
        is_values = {k: float(data[k]) for k in INCOME_STATEMENT_KEYS if _is_number(data.get(k))}
        statement = FinancialStatement(
            company=str(data.get("company", "Unknown")),
            period=str(data.get("period", "Unknown")),
            currency=str(data.get("currency", "COP")),
            balance_sheet=BalanceSheet(**bs_values),
            income_statement=IncomeStatement(**is_values),
        )
        found = list(bs_values) + list(is_values)
        return ExtractionResult(statement=statement, method="llm", found_keys=found)


def _parse_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) or (
        isinstance(value, str) and value.replace(".", "", 1).replace("-", "", 1).isdigit()
    )

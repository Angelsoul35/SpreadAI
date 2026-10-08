"""Write a short credit memo from the spread statement and its ratios.

Two modes:

* ``template`` (default) builds the memo from the numbers with no LLM. It always
  works, offline and free.
* ``llm`` asks the provider cascade to write the memo. It reads better, but needs
  a provider and a key. In tests we inject a fake client.
"""

from __future__ import annotations

from .llm import LLMClient, build_llm
from .ratios import compute_ratios
from .schema import FinancialStatement
from .validate import ValidationResult


def _fmt_ratio(value: float | None, pct: bool = False) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%" if pct else f"{value:.2f}"


def template_memo(statement: FinancialStatement, validation: ValidationResult) -> str:
    """A deterministic credit memo built from the numbers."""
    r = compute_ratios(statement)
    s = statement.summary()
    lines = [
        f"CREDIT MEMO — {statement.company} ({statement.period})",
        "",
        f"Total assets: {s['total_assets']:,.0f} {statement.currency}. "
        f"Total liabilities: {s['total_liabilities']:,.0f}. "
        f"Equity: {s['total_equity']:,.0f}.",
        f"Revenue: {s['revenue']:,.0f}. Net income: {s['net_income']:,.0f}.",
        "",
        "Key ratios:",
        f"  Current ratio: {_fmt_ratio(r['current_ratio'])} "
        f"(liquidity; above 1.0 means current assets cover current liabilities).",
        f"  Debt-to-equity: {_fmt_ratio(r['debt_to_equity'])} "
        f"(leverage; higher means more debt relative to equity).",
        f"  Interest coverage: {_fmt_ratio(r['interest_coverage'])} "
        f"(operating income over interest; higher is safer).",
        f"  Net margin: {_fmt_ratio(r['net_margin'], pct=True)}.",
        f"  Return on equity: {_fmt_ratio(r['return_on_equity'], pct=True)}.",
        "",
        "Data quality:",
        f"  Accounting identity balanced: {'yes' if validation.balanced else 'NO'}.",
        f"  Extraction confidence: {validation.confidence:.0%}.",
    ]
    if validation.confidence < 0.8 or not validation.balanced:
        lines.append("  NOTE: low confidence or unbalanced — send to human review before use.")
    return "\n".join(lines)


_SYSTEM = (
    "You are a credit analyst. Write a short, factual credit memo (120-180 words) "
    "from the given financial data and ratios. Be neutral; do not invent numbers."
)


def llm_memo(
    statement: FinancialStatement,
    validation: ValidationResult,
    llm: LLMClient | None = None,
    provider_spec: str | None = None,
) -> str:
    """A credit memo written by the LLM cascade."""
    client = llm or (build_llm(provider_spec) if provider_spec else build_llm())
    r = compute_ratios(statement)
    prompt = (
        f"Company: {statement.company} ({statement.period}), currency {statement.currency}.\n"
        f"Summary: {statement.summary()}\n"
        f"Ratios: {r}\n"
        f"Balanced: {validation.balanced}. Confidence: {validation.confidence:.0%}.\n"
        "Write the credit memo."
    )
    return client.complete(_SYSTEM, prompt, max_tokens=400).text.strip()

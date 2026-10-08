"""Financial ratios used in credit analysis.

Each ratio returns ``None`` when its denominator is zero, so a missing or empty
line item does not crash the analysis.
"""

from __future__ import annotations

from .schema import FinancialStatement


def _safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def compute_ratios(statement: FinancialStatement) -> dict[str, float | None]:
    bs = statement.balance_sheet
    is_ = statement.income_statement

    ratios: dict[str, float | None] = {
        # Liquidity
        "current_ratio": _safe_div(bs.total_current_assets, bs.total_current_liabilities),
        "quick_ratio": _safe_div(
            bs.total_current_assets - bs.inventory, bs.total_current_liabilities
        ),
        # Leverage
        "debt_to_equity": _safe_div(bs.total_debt, bs.total_equity),
        "debt_to_assets": _safe_div(bs.total_liabilities, bs.total_assets),
        "interest_coverage": _safe_div(is_.operating_income, is_.interest_expense),
        # Profitability
        "gross_margin": _safe_div(is_.gross_profit, is_.revenue),
        "operating_margin": _safe_div(is_.operating_income, is_.revenue),
        "net_margin": _safe_div(is_.net_income, is_.revenue),
        "return_on_assets": _safe_div(is_.net_income, bs.total_assets),
        "return_on_equity": _safe_div(is_.net_income, bs.total_equity),
    }
    return {k: (round(v, 4) if v is not None else None) for k, v in ratios.items()}

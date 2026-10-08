"""Check an extracted statement and score how much we trust it.

The main check is the accounting identity: assets must equal liabilities plus
equity. If that fails, the extraction is probably wrong or the statement is odd,
so the confidence drops and the case should go to a human. We also check a few
sanity rules (revenue present, no negative core items).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .schema import FinancialStatement


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


@dataclass
class ValidationResult:
    checks: list[Check] = field(default_factory=list)
    balanced: bool = False
    confidence: float = 0.0

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def as_dict(self) -> dict:
        return {
            "balanced": self.balanced,
            "confidence": round(self.confidence, 4),
            "passed": self.passed,
            "checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail}
                for c in self.checks
            ],
        }


def validate(
    statement: FinancialStatement,
    field_coverage: float,
    balance_tolerance: float = 0.01,
) -> ValidationResult:
    bs = statement.balance_sheet
    is_ = statement.income_statement
    checks: list[Check] = []

    assets = bs.total_assets
    liab_plus_equity = bs.total_liabilities + bs.total_equity
    denom = max(abs(assets), 1.0)
    rel_error = abs(assets - liab_plus_equity) / denom
    balanced = rel_error <= balance_tolerance
    checks.append(
        Check(
            name="accounting_identity",
            passed=balanced,
            detail=(
                f"assets={assets:,.0f} vs L+E={liab_plus_equity:,.0f} "
                f"(rel error {rel_error:.4f})"
            ),
        )
    )

    revenue_ok = is_.revenue > 0
    checks.append(Check("revenue_present", revenue_ok, f"revenue={is_.revenue:,.0f}"))

    core = {
        "cash": bs.cash,
        "inventory": bs.inventory,
        "revenue": is_.revenue,
        "total_assets": assets,
    }
    negatives = [k for k, v in core.items() if v < 0]
    checks.append(
        Check("no_negative_core_items", not negatives, f"negative: {negatives or 'none'}")
    )

    confidence = field_coverage
    if not balanced:
        confidence *= 0.4
    if not revenue_ok:
        confidence *= 0.6
    if negatives:
        confidence *= 0.7
    confidence = round(min(1.0, max(0.0, confidence)), 4)

    return ValidationResult(checks=checks, balanced=balanced, confidence=confidence)

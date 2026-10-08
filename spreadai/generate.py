"""Generate synthetic financial statements and render them to text or PDF.

Everything here is fake and deterministic. The generator builds a balance sheet
whose accounting identity holds by construction (assets = liabilities + equity),
so a correctly extracted statement always validates. This gives us known-good
inputs to test the extractor, the validator, and the ratios against.
"""

from __future__ import annotations

import argparse

import numpy as np

from .labels import PRIMARY_LABELS
from .schema import BalanceSheet, FinancialStatement, IncomeStatement

_COMPANIES = [
    "Andes Manufacturing SAS",
    "Caribe Logistics SAS",
    "Pacifico Foods SAS",
    "Orinoco Energy SAS",
]


def make_statement(seed: int = 7) -> FinancialStatement:
    """Return a synthetic, internally consistent financial statement."""
    rng = np.random.default_rng(seed)

    # Assets (in COP, millions scaled up).
    cash = float(rng.integers(50, 500) * 1_000_000)
    accounts_receivable = float(rng.integers(100, 900) * 1_000_000)
    inventory = float(rng.integers(100, 1200) * 1_000_000)
    other_current_assets = float(rng.integers(20, 200) * 1_000_000)
    ppe = float(rng.integers(500, 4000) * 1_000_000)
    other_noncurrent_assets = float(rng.integers(50, 600) * 1_000_000)

    bs = BalanceSheet(
        cash=cash,
        accounts_receivable=accounts_receivable,
        inventory=inventory,
        other_current_assets=other_current_assets,
        property_plant_equipment=ppe,
        other_noncurrent_assets=other_noncurrent_assets,
    )
    total_assets = bs.total_assets

    # Liabilities as a share of assets, then equity is the remainder so that
    # assets = liabilities + equity holds exactly.
    leverage = float(rng.uniform(0.35, 0.70))
    total_liabilities = round(total_assets * leverage, 2)

    accounts_payable = round(total_liabilities * float(rng.uniform(0.15, 0.30)), 2)
    short_term_debt = round(total_liabilities * float(rng.uniform(0.10, 0.25)), 2)
    other_current_liabilities = round(total_liabilities * float(rng.uniform(0.05, 0.15)), 2)
    long_term_debt = round(total_liabilities * float(rng.uniform(0.25, 0.45)), 2)
    other_noncurrent_liabilities = round(
        total_liabilities
        - accounts_payable
        - short_term_debt
        - other_current_liabilities
        - long_term_debt,
        2,
    )

    total_equity = round(total_assets - total_liabilities, 2)
    retained_earnings = round(total_equity * float(rng.uniform(0.3, 0.7)), 2)
    common_equity = round(total_equity - retained_earnings, 2)

    bs.accounts_payable = accounts_payable
    bs.short_term_debt = short_term_debt
    bs.other_current_liabilities = other_current_liabilities
    bs.long_term_debt = long_term_debt
    bs.other_noncurrent_liabilities = other_noncurrent_liabilities
    bs.common_equity = common_equity
    bs.retained_earnings = retained_earnings

    # Income statement, loosely scaled to assets.
    revenue = round(total_assets * float(rng.uniform(0.8, 1.8)), 2)
    cogs = round(revenue * float(rng.uniform(0.55, 0.75)), 2)
    opex = round(revenue * float(rng.uniform(0.10, 0.20)), 2)
    interest = round(bs.total_debt * float(rng.uniform(0.08, 0.14)), 2)
    pretax = revenue - cogs - opex - interest
    tax = round(max(pretax, 0) * 0.30, 2)

    is_ = IncomeStatement(
        revenue=revenue,
        cost_of_goods_sold=cogs,
        operating_expenses=opex,
        interest_expense=interest,
        tax_expense=tax,
    )

    company = _COMPANIES[int(rng.integers(0, len(_COMPANIES)))]
    year = int(rng.integers(2021, 2026))
    return FinancialStatement(
        company=company, period=f"FY{year}", currency="COP",
        balance_sheet=bs, income_statement=is_,
    )


def _fmt(amount: float) -> str:
    return f"{amount:,.0f}"


def render_text(stmt: FinancialStatement) -> str:
    """Render a statement as labelled text that the parser can read back."""
    bs, is_ = stmt.balance_sheet, stmt.income_statement
    lines = [
        f"Company: {stmt.company}",
        f"Period: {stmt.period}",
        f"Currency: {stmt.currency}",
        "",
        "BALANCE SHEET",
        "Assets",
    ]
    for key in ["cash", "accounts_receivable", "inventory", "other_current_assets",
                "property_plant_equipment", "other_noncurrent_assets"]:
        lines.append(f"{PRIMARY_LABELS[key]}: {_fmt(getattr(bs, key))}")
    lines.append("Liabilities")
    for key in ["accounts_payable", "short_term_debt", "other_current_liabilities",
                "long_term_debt", "other_noncurrent_liabilities"]:
        lines.append(f"{PRIMARY_LABELS[key]}: {_fmt(getattr(bs, key))}")
    lines.append("Equity")
    for key in ["common_equity", "retained_earnings"]:
        lines.append(f"{PRIMARY_LABELS[key]}: {_fmt(getattr(bs, key))}")
    lines += ["", "INCOME STATEMENT"]
    for key in ["revenue", "cost_of_goods_sold", "operating_expenses",
                "interest_expense", "tax_expense"]:
        lines.append(f"{PRIMARY_LABELS[key]}: {_fmt(getattr(is_, key))}")
    return "\n".join(lines)


def render_pdf(stmt: FinancialStatement, path: str) -> str:
    """Render a statement as a text-based PDF (readable by pdfplumber)."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter
    y = height - 50
    c.setFont("Helvetica", 11)
    for line in render_text(stmt).split("\n"):
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - 50
        c.drawString(50, y, line)
        y -= 16
    c.save()
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic financial statement.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--pdf", default="out/sample_statement.pdf")
    args = parser.parse_args()
    stmt = make_statement(args.seed)
    path = render_pdf(stmt, args.pdf)
    print(f"Wrote {path} for {stmt.company} ({stmt.period})")


if __name__ == "__main__":
    main()

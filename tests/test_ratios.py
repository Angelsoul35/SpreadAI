from __future__ import annotations

from spreadai.ratios import compute_ratios
from spreadai.schema import BalanceSheet, FinancialStatement, IncomeStatement


def test_ratios_on_generated_statement(statement):
    r = compute_ratios(statement)
    assert r["current_ratio"] is not None and r["current_ratio"] > 0
    assert r["net_margin"] is not None
    assert -1 <= r["net_margin"] <= 1


def test_ratios_handle_zero_denominators():
    empty = FinancialStatement(balance_sheet=BalanceSheet(), income_statement=IncomeStatement())
    r = compute_ratios(empty)
    assert r["current_ratio"] is None  # no current liabilities
    assert r["net_margin"] is None  # no revenue
    assert r["interest_coverage"] is None  # no interest expense


def test_known_ratio_values():
    bs = BalanceSheet(cash=200, accounts_payable=100, common_equity=100, short_term_debt=50)
    is_ = IncomeStatement(revenue=1000, cost_of_goods_sold=600)
    stmt = FinancialStatement(balance_sheet=bs, income_statement=is_)
    r = compute_ratios(stmt)
    # current assets 200 / current liabilities 150 = 1.3333
    assert round(r["current_ratio"], 4) == round(200 / 150, 4)
    # gross profit 400 / revenue 1000 = 0.4
    assert r["gross_margin"] == 0.4

from __future__ import annotations

from spreadai.extract.base import parse_amount
from spreadai.extract.text_parser import parse_text
from spreadai.validate import validate


def test_parse_amount_variants():
    assert parse_amount("1,234,567") == 1234567.0
    assert parse_amount("$ 1,000") == 1000.0
    assert parse_amount("(1,234)") == -1234.0
    assert parse_amount("") is None
    assert parse_amount("n/a") is None


def test_text_round_trip_recovers_all_items(statement, statement_text):
    result = parse_text(statement_text)
    assert result.field_coverage == 1.0
    assert result.statement.company == statement.company
    assert round(result.statement.balance_sheet.total_assets) == round(
        statement.balance_sheet.total_assets
    )


def test_aliases_are_recognised():
    text = "Sales: 1,000\nCOGS: 600\nTrade receivables: 200"
    result = parse_text(text)
    assert result.statement.income_statement.revenue == 1000
    assert result.statement.income_statement.cost_of_goods_sold == 600
    assert result.statement.balance_sheet.accounts_receivable == 200


def test_generated_statement_balances(statement):
    v = validate(statement, field_coverage=1.0)
    assert v.balanced is True
    assert v.confidence == 1.0
    assert v.passed is True


def test_unbalanced_statement_lowers_confidence(statement):
    statement.balance_sheet.retained_earnings += 999_000_000_000
    v = validate(statement, field_coverage=1.0)
    assert v.balanced is False
    assert v.confidence < 0.8
    assert any(c.name == "accounting_identity" and not c.passed for c in v.checks)


def test_low_coverage_lowers_confidence():
    text = "Company: X\nCash and cash equivalents: 100\nRevenue: 1000"
    result = parse_text(text)
    assert result.field_coverage < 0.3
    v = validate(result.statement, result.field_coverage)
    assert v.confidence < 0.5

"""The standard shape of a spread financial statement.

"Spreading" a statement means taking a company's balance sheet and income
statement and putting the numbers into one fixed schema, so that any statement
can be compared and checked the same way. These models are that fixed schema.
All amounts are in the statement's reporting currency.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Canonical line-item keys. Extraction maps messy labels onto these.
BALANCE_SHEET_KEYS: list[str] = [
    "cash",
    "accounts_receivable",
    "inventory",
    "other_current_assets",
    "property_plant_equipment",
    "other_noncurrent_assets",
    "accounts_payable",
    "short_term_debt",
    "other_current_liabilities",
    "long_term_debt",
    "other_noncurrent_liabilities",
    "common_equity",
    "retained_earnings",
]

INCOME_STATEMENT_KEYS: list[str] = [
    "revenue",
    "cost_of_goods_sold",
    "operating_expenses",
    "interest_expense",
    "tax_expense",
]


class BalanceSheet(BaseModel):
    cash: float = 0.0
    accounts_receivable: float = 0.0
    inventory: float = 0.0
    other_current_assets: float = 0.0
    property_plant_equipment: float = 0.0
    other_noncurrent_assets: float = 0.0

    accounts_payable: float = 0.0
    short_term_debt: float = 0.0
    other_current_liabilities: float = 0.0
    long_term_debt: float = 0.0
    other_noncurrent_liabilities: float = 0.0

    common_equity: float = 0.0
    retained_earnings: float = 0.0

    @property
    def total_current_assets(self) -> float:
        return self.cash + self.accounts_receivable + self.inventory + self.other_current_assets

    @property
    def total_noncurrent_assets(self) -> float:
        return self.property_plant_equipment + self.other_noncurrent_assets

    @property
    def total_assets(self) -> float:
        return self.total_current_assets + self.total_noncurrent_assets

    @property
    def total_current_liabilities(self) -> float:
        return self.accounts_payable + self.short_term_debt + self.other_current_liabilities

    @property
    def total_noncurrent_liabilities(self) -> float:
        return self.long_term_debt + self.other_noncurrent_liabilities

    @property
    def total_liabilities(self) -> float:
        return self.total_current_liabilities + self.total_noncurrent_liabilities

    @property
    def total_equity(self) -> float:
        return self.common_equity + self.retained_earnings

    @property
    def total_debt(self) -> float:
        return self.short_term_debt + self.long_term_debt


class IncomeStatement(BaseModel):
    revenue: float = 0.0
    cost_of_goods_sold: float = 0.0
    operating_expenses: float = 0.0
    interest_expense: float = 0.0
    tax_expense: float = 0.0

    @property
    def gross_profit(self) -> float:
        return self.revenue - self.cost_of_goods_sold

    @property
    def operating_income(self) -> float:
        return self.gross_profit - self.operating_expenses

    @property
    def pretax_income(self) -> float:
        return self.operating_income - self.interest_expense

    @property
    def net_income(self) -> float:
        return self.pretax_income - self.tax_expense


class FinancialStatement(BaseModel):
    company: str = "Unknown"
    period: str = "Unknown"
    currency: str = "COP"
    balance_sheet: BalanceSheet = Field(default_factory=BalanceSheet)
    income_statement: IncomeStatement = Field(default_factory=IncomeStatement)

    def summary(self) -> dict:
        bs, is_ = self.balance_sheet, self.income_statement
        return {
            "company": self.company,
            "period": self.period,
            "currency": self.currency,
            "total_assets": round(bs.total_assets, 2),
            "total_liabilities": round(bs.total_liabilities, 2),
            "total_equity": round(bs.total_equity, 2),
            "revenue": round(is_.revenue, 2),
            "net_income": round(is_.net_income, 2),
        }

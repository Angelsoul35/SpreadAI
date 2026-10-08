"""Labels for each line item, and alternative labels (aliases) for parsing.

The generator uses the primary label. The text parser accepts the primary label
or any alias, so a statement that says "Sales" or "COGS" still maps to the right
canonical key. Matching is case-insensitive.
"""

from __future__ import annotations

PRIMARY_LABELS: dict[str, str] = {
    "cash": "Cash and cash equivalents",
    "accounts_receivable": "Accounts receivable",
    "inventory": "Inventory",
    "other_current_assets": "Other current assets",
    "property_plant_equipment": "Property, plant and equipment",
    "other_noncurrent_assets": "Other non-current assets",
    "accounts_payable": "Accounts payable",
    "short_term_debt": "Short-term debt",
    "other_current_liabilities": "Other current liabilities",
    "long_term_debt": "Long-term debt",
    "other_noncurrent_liabilities": "Other non-current liabilities",
    "common_equity": "Common equity",
    "retained_earnings": "Retained earnings",
    "revenue": "Revenue",
    "cost_of_goods_sold": "Cost of goods sold",
    "operating_expenses": "Operating expenses",
    "interest_expense": "Interest expense",
    "tax_expense": "Income tax expense",
}

ALIASES: dict[str, list[str]] = {
    "cash": ["cash", "cash & cash equivalents"],
    "accounts_receivable": ["trade receivables", "receivables", "debtors"],
    "property_plant_equipment": ["ppe", "fixed assets", "property plant and equipment"],
    "short_term_debt": ["short term debt", "current borrowings", "short-term borrowings"],
    "long_term_debt": ["long term debt", "non-current borrowings", "long-term borrowings"],
    "accounts_payable": ["trade payables", "payables", "creditors"],
    "revenue": ["sales", "net sales", "total revenue", "turnover"],
    "cost_of_goods_sold": ["cogs", "cost of sales"],
    "operating_expenses": ["opex", "sg&a", "selling general and administrative"],
    "interest_expense": ["finance costs", "interest"],
    "tax_expense": ["income tax", "taxes", "tax"],
    "retained_earnings": ["accumulated earnings", "retained profit"],
}


def label_lookup() -> dict[str, str]:
    """Return a map from a lowercased label/alias to its canonical key."""
    out: dict[str, str] = {}
    for key, label in PRIMARY_LABELS.items():
        out[label.lower()] = key
    for key, aliases in ALIASES.items():
        for alias in aliases:
            out[alias.lower()] = key
    return out

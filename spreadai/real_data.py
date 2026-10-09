"""Load and spread a real dataset of U.S. public-company financial statements.

The headline validation of SpreadAI does not run on generated statements: it runs
on the **American Bankruptcy** dataset (Lombardo et al., *Future Internet* 2022),
a panel of U.S. public companies from Compustat covering 1999-2018. Each record is
a company with three consecutive fiscal years of accounting line items and a
forward-looking label (``failed`` = filed for Chapter 7/11 the following year,
``alive`` otherwise).

Every record is pushed through SpreadAI's *own* pipeline end to end:

    raw line items -> labelled statement text -> ``parse_text`` (the real extractor)
    -> ``validate`` (accounting identity + confidence) -> ``compute_ratios``

so the feature vector handed to the downstream classifier in ``real_benchmark`` is
produced by the same code that serves the API. Nothing here is synthetic.

A snapshot of the three official splits is vendored under ``datasets/`` so the
benchmark and the tests run fully offline. ``fetch_american_bankruptcy`` regenerates
that snapshot from the public source; its network call goes through the
module-level ``urlopen`` seam, which the tests monkeypatch.

Source: https://github.com/sowide/bankruptcy_dataset (CC-BY-4.0). See
``datasets/README.md`` for the full field/label mapping and regeneration steps.
"""

from __future__ import annotations

import csv
import io
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .extract.text_parser import parse_text
from .labels import PRIMARY_LABELS
from .ratios import compute_ratios
from .schema import FinancialStatement
from .validate import ValidationResult, validate

# --- source + snapshot location ------------------------------------------------

SOURCE_URL = "https://raw.githubusercontent.com/sowide/bankruptcy_dataset/main/dataset_paper.zip"
DATA_DIR = Path(__file__).resolve().parent.parent / "datasets" / "american_bankruptcy"

SPLITS: dict[str, str] = {
    "train": "financial_train.csv",
    "validation": "financial_validation.csv",
    "test": "financial_test.csv",
}
# Path of each split inside the published archive.
_ARCHIVE_MEMBERS = {split: f"dataset_paper/{name}" for split, name in SPLITS.items()}

# The 18 accounting line items present for each of the three years in a record.
# Column names in the CSV are ``<year>_<field>`` with year in {1, 2, 3} (3 = newest).
FEATURE_FIELDS: tuple[str, ...] = (
    "current_assets",
    "total_assets",
    "cost_of_goods_sold",
    "total_long_term_debt",
    "depreciation_and_amortization",
    "ebit",
    "ebitda",
    "gross_profit",
    "inventory",
    "total_current_liabilities",
    "net_income",
    "retained_earnings",
    "total_receivables",
    "total_revenue",
    "market_value",
    "total_liabilities",
    "net_sales",
    "total_operating_expenses",
)

# Years in a record, oldest to newest. "3" is the fiscal year the label refers to.
YEAR_PREFIXES: tuple[str, ...] = ("1", "2", "3")

# Ratios SpreadAI computes that are informative on this dataset. ``interest_coverage``
# is dropped: the source reports no interest-expense line, so it is always undefined.
RATIO_FEATURES: tuple[str, ...] = (
    "current_ratio",
    "quick_ratio",
    "debt_to_equity",
    "debt_to_assets",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "return_on_assets",
    "return_on_equity",
)

# The labelled line items the text renderer emits (canonical key -> value source).
# Equity is split so the accounting identity holds exactly, matching real balance
# sheets where common equity is paid-in capital plus reserves (the balancing item).

_FAILED = "failed"


# --- network fetch (regenerates the vendored snapshot) -------------------------

# Monkeypatchable seam: tests replace this to run offline.
urlopen = urllib.request.urlopen


class FetchError(RuntimeError):
    """Raised when the dataset could not be downloaded after all retries."""


def fetch_american_bankruptcy(
    dest: Path | str = DATA_DIR,
    *,
    retries: int = 4,
    backoff_base: float = 2.0,
    timeout: float = 60.0,
    sleep=time.sleep,
) -> dict[str, Path]:
    """Download the published archive and extract the three splits into ``dest``.

    The request is retried up to ``retries`` times with exponential backoff
    (``backoff_base`` ** attempt seconds) on any network error. On success the
    three CSV splits are written and a mapping ``split -> path`` is returned.
    Raises :class:`FetchError` if every attempt fails.
    """
    dest = Path(dest)
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(SOURCE_URL, timeout=timeout) as response:
                payload = response.read()
            break
        except Exception as exc:  # network/URL/timeout errors are all retryable
            last_error = exc
            if attempt < retries - 1:
                sleep(backoff_base**attempt)
    else:
        raise FetchError(
            f"could not download {SOURCE_URL} after {retries} attempts: {last_error}"
        ) from last_error

    dest.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for split, member in _ARCHIVE_MEMBERS.items():
            out = dest / SPLITS[split]
            out.write_bytes(archive.read(member))
            written[split] = out
    return written


# --- reading the vendored snapshot ---------------------------------------------


def iter_records(split: str = "train", *, data_dir: Path | str = DATA_DIR) -> list[dict[str, str]]:
    """Return the raw rows of a split from the vendored snapshot."""
    if split not in SPLITS:
        raise ValueError(f"unknown split {split!r}; choose from {sorted(SPLITS)}")
    path = Path(data_dir) / SPLITS[split]
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing; run spreadai.real_data.fetch_american_bankruptcy() "
            "to regenerate the snapshot"
        )
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def label_of(record: dict[str, str]) -> int:
    """1 if the company failed the following year, else 0."""
    return 1 if record["status_label"].strip().lower() == _FAILED else 0


# --- spreading one company-year through the real pipeline ----------------------


def _field(record: dict[str, str], prefix: str, name: str) -> float:
    return float(record[f"{prefix}_{name}"])


def render_statement_text(record: dict[str, str], prefix: str) -> str:
    """Render one fiscal year of a record as SpreadAI-readable labelled text.

    Raw line items are mapped onto SpreadAI's canonical schema. Equity is the
    balancing item (total assets - total liabilities), exactly as on a real
    balance sheet, so the accounting identity holds and the extraction validates.
    """
    g = lambda name: _field(record, prefix, name)  # noqa: E731
    current_assets = g("current_assets")
    total_assets = g("total_assets")
    inventory = g("inventory")
    receivables = g("total_receivables")
    current_liabilities = g("total_current_liabilities")
    long_term_debt = g("total_long_term_debt")
    total_liabilities = g("total_liabilities")
    retained_earnings = g("retained_earnings")
    revenue = g("total_revenue")
    cogs = g("cost_of_goods_sold")
    gross_profit = g("gross_profit")
    ebit = g("ebit")
    net_income = g("net_income")

    values: dict[str, float] = {
        # Assets: receivables and inventory broken out (quick ratio needs them);
        # the rest of current assets and all non-current assets kept as residuals.
        "accounts_receivable": receivables,
        "inventory": inventory,
        "other_current_assets": max(current_assets - inventory - receivables, 0.0),
        "property_plant_equipment": max(total_assets - current_assets, 0.0),
        # Liabilities: long-term debt is the only interest-bearing line reported.
        "other_current_liabilities": current_liabilities,
        "long_term_debt": long_term_debt,
        "other_noncurrent_liabilities": max(
            total_liabilities - current_liabilities - long_term_debt, 0.0
        ),
        # Equity: retained earnings reported; common equity balances the sheet.
        "retained_earnings": retained_earnings,
        "common_equity": (total_assets - total_liabilities) - retained_earnings,
        # Income statement: operating expenses set so operating income == EBIT;
        # tax_expense absorbs below-operating items (no interest line in source).
        "revenue": revenue,
        "cost_of_goods_sold": cogs,
        "operating_expenses": gross_profit - ebit,
        "tax_expense": ebit - net_income,
    }

    lines = [
        f"Company: {record.get('cik', 'Unknown')}",
        f"Period: FY{int(float(record['fyear']))}",
        "Currency: USD",
    ]
    for key, amount in values.items():
        # 4 decimals is lossless for this source (line items carry <=4 decimals) and
        # the thousands separators exercise SpreadAI's money parser on the way back in.
        lines.append(f"{PRIMARY_LABELS[key]}: {amount:,.4f}")
    return "\n".join(lines)


def spread_year(record: dict[str, str], prefix: str) -> tuple[FinancialStatement, ValidationResult]:
    """Run the real extractor + validator on one fiscal year of a record."""
    extraction = parse_text(render_statement_text(record, prefix))
    validation = validate(extraction.statement, extraction.field_coverage)
    return extraction.statement, validation


def ratio_vector(statement: FinancialStatement) -> list[float]:
    """SpreadAI's ratios for a statement, as a float vector (NaN where undefined)."""
    ratios = compute_ratios(statement)
    out: list[float] = []
    for key in RATIO_FEATURES:
        value = ratios[key]
        out.append(float(value) if value is not None and np.isfinite(value) else np.nan)
    return out


def feature_names() -> list[str]:
    """Names of the 36 features: 9 ratios per year (y1,y2,y3) plus 3-year trends."""
    names = [f"{r}_y{p}" for p in YEAR_PREFIXES for r in RATIO_FEATURES]
    names += [f"{r}_trend" for r in RATIO_FEATURES]
    return names


@dataclass
class RealDataset:
    X: np.ndarray
    y: np.ndarray
    names: list[str]
    coverage: np.ndarray  # extraction field-coverage per record (newest year)
    balanced: np.ndarray  # whether the newest-year spread satisfied the identity

    @property
    def n_positive(self) -> int:
        return int(self.y.sum())

    @property
    def prevalence(self) -> float:
        return float(self.y.mean())


def load_dataset(split: str = "train", *, data_dir: Path | str = DATA_DIR) -> RealDataset:
    """Spread every record of a split and return the model-ready feature matrix.

    Features per record: SpreadAI's nine ratios for each of the three fiscal years,
    followed by each ratio's newest-minus-oldest trend (36 features total). The
    whole statement is produced by SpreadAI's text extractor and validator, so a
    model trained on ``X`` is trained on what SpreadAI actually outputs.
    """
    records = iter_records(split, data_dir=data_dir)
    rows, labels, coverage, balanced = [], [], [], []
    for record in records:
        per_year: list[list[float]] = []
        newest_coverage = 0.0
        newest_balanced = False
        for prefix in YEAR_PREFIXES:
            extraction = parse_text(render_statement_text(record, prefix))
            per_year.append(ratio_vector(extraction.statement))
            # coverage/validation reported on the newest year (the labelled one)
            newest_coverage = extraction.field_coverage
            newest_balanced = validate(extraction.statement, extraction.field_coverage).balanced
        feats: list[float] = [v for year in per_year for v in year]
        # trend: newest (y3) minus oldest (y1) for each ratio
        for j in range(len(RATIO_FEATURES)):
            oldest, newest = per_year[0][j], per_year[-1][j]
            feats.append(newest - oldest if np.isfinite(oldest) and np.isfinite(newest) else np.nan)
        rows.append(feats)
        labels.append(label_of(record))
        coverage.append(newest_coverage)
        balanced.append(1.0 if newest_balanced else 0.0)

    return RealDataset(
        X=np.asarray(rows, dtype=float),
        y=np.asarray(labels, dtype=int),
        names=feature_names(),
        coverage=np.asarray(coverage, dtype=float),
        balanced=np.asarray(balanced, dtype=float),
    )

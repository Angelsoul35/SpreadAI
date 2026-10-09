# American Bankruptcy dataset (vendored snapshot)

This directory holds a vendored snapshot of a **real** dataset of U.S. public-company
financial statements, used to validate SpreadAI end to end on data it did not generate.
The snapshot lets the benchmark and the tests run fully offline.

## Source

* **Dataset:** American Bankruptcy dataset — accounting line items for U.S. public
  companies with a forward-looking bankruptcy label.
* **Origin:** <https://github.com/sowide/bankruptcy_dataset> (file `dataset_paper.zip`,
  the paper's train/validation/test splits).
* **Papers:**
  * Lombardo, G., Pellegrino, M., Adosoglou, G., Cagnoni, S., Pardalos, P. M., & Poggi, A.
    (2022). *Machine Learning for Bankruptcy Prediction in the American Stock Market:
    Dataset and Benchmarks.* Future Internet, 14(8), 244.
  * Pellegrino, M., Lombardo, G., et al. (2024). *A Multi-Head LSTM Architecture for
    Bankruptcy Prediction with Time Series Accounting Data.* Future Internet, 16(3), 79.
* **Underlying data:** firm fundamentals from Compustat / S&P Capital IQ; bankruptcy events
  from the UCLA-LoPucki Bankruptcy Research Database.
* **License:** CC-BY-4.0 (attribution). Company identifiers are anonymized to `C1`, `C2`, …
* **Coverage:** 1999–2018. The published panel windows three consecutive fiscal years per
  company.

## Files (snapshot)

| File | Rows | Prediction year | Failed |
|---|---|---|---|
| `american_bankruptcy/financial_train.csv` | 3,142 | 2001–2014 | 403 |
| `american_bankruptcy/financial_validation.csv` | 233 | 2015 | 27 |
| `american_bankruptcy/financial_test.csv` | 2,815 | 2016–2018 | 72 |

Each row is one company window: `cik`, `fyear`, `status_label` (`alive` / `failed`), then
**18 line items for each of 3 years**, named `<year>_<field>` where `year ∈ {1, 2, 3}` and
`3` is the most recent year (the one the label looks forward from).

`status_label = failed` means the company filed for Chapter 7/11 in the year **after** the
window — it is a forward-looking distress label, not a contemporaneous one.

## Field → SpreadAI schema mapping

The 18 source fields per year are
`current_assets, total_assets, cost_of_goods_sold, total_long_term_debt,
depreciation_and_amortization, ebit, ebitda, gross_profit, inventory,
total_current_liabilities, net_income, retained_earnings, total_receivables,
total_revenue, market_value, total_liabilities, net_sales, total_operating_expenses`.

`spreadai/real_data.py` renders each year as a labelled statement and parses it back with
SpreadAI's own `parse_text`, so the mapping below is what actually reaches the pipeline:

| SpreadAI canonical line | Source field(s) |
|---|---|
| `accounts_receivable` | `total_receivables` |
| `inventory` | `inventory` |
| `other_current_assets` | `current_assets − inventory − total_receivables` (≥ 0) |
| `property_plant_equipment` | `total_assets − current_assets` (≥ 0; all non-current assets) |
| `other_current_liabilities` | `total_current_liabilities` |
| `long_term_debt` | `total_long_term_debt` (only interest-bearing line reported) |
| `other_noncurrent_liabilities` | `total_liabilities − total_current_liabilities − total_long_term_debt` (≥ 0) |
| `retained_earnings` | `retained_earnings` |
| `common_equity` | `(total_assets − total_liabilities) − retained_earnings` (balancing item) |
| `revenue` | `total_revenue` (equals `net_sales` throughout the dataset) |
| `cost_of_goods_sold` | `cost_of_goods_sold` |
| `operating_expenses` | `gross_profit − ebit` (so SpreadAI's operating income = EBIT) |
| `tax_expense` | `ebit − net_income` (absorbs below-operating items) |

Mapping notes and caveats (what is and is not faithful):

* **Equity is the balancing item** — exactly how a real balance sheet works (common equity
  is paid-in capital plus reserves, the figure that makes assets = liabilities + equity).
  The identity therefore holds and the spread validates.
* **No interest line** is reported, so `interest_expense = 0` and SpreadAI's
  `interest_coverage` is undefined on this source; it is dropped from the feature set.
* **No cash / payables / short-term-debt split** is reported. Those canonical lines are left
  at zero or folded into residuals, which is why extraction coverage is 13/18 ≈ 0.722. The
  ratios SpreadAI computes do not depend on the missing lines.
* The mapping preserves every accounting identity present in the source: it was verified
  that `gross_profit = total_revenue − cost_of_goods_sold`, `ebitda = total_revenue −
  total_operating_expenses`, and `ebit = ebitda − depreciation_and_amortization` hold on the
  snapshot rows.

## Regeneration

The snapshot is produced by the fetcher, which downloads the public archive (with retries
and a monkeypatchable `urlopen` seam) and extracts the three splits:

```python
from spreadai.real_data import fetch_american_bankruptcy
fetch_american_bankruptcy()   # writes the three CSVs into datasets/american_bankruptcy/
```

## SHA-256 of the vendored files

```
a4a952bee192b24afda0749d45873d02b86456836773b7e6d4cf3e6408a1fd78  financial_train.csv
96ea45de1923c677c608e203332231dda9501f27ed8def473f1f4a76350856b9  financial_validation.csv
ec1791d2ce7e0c925149d0eb2f706d8f6a9514f6cfb8ac3e2ff9a95dd8799e6d  financial_test.csv
```

"""Functional tests for the real-data path.

Each test fails if the behaviour it guards actually breaks: the loader must return
the real panel with the right shape and labels; the spread of a known failed company
must produce the distress ratios by hand-check; the pipeline must beat the baseline
on the held-out years; the verdict must tell a real fit from a shuffled one; and the
offline fetch must retry and then either succeed or exhaust.
"""

from __future__ import annotations

import io
import zipfile

import numpy as np
import pytest

from spreadai import real_data
from spreadai.real_benchmark import (
    AGREEMENT_TOLERANCE,
    BenchmarkResult,
    classify_fit,
    format_report,
    run_benchmark,
)
from spreadai.real_data import (
    SPLITS,
    FetchError,
    RealDataset,
    fetch_american_bankruptcy,
    iter_records,
    label_of,
    spread_year,
)

# ---------------------------------------------------------------- loader shape


def test_train_split_has_expected_shape_and_labels(real_train: RealDataset):
    # 3142 companies, 36 features (9 ratios x 3 years + 9 trends), 403 failures.
    assert real_train.X.shape == (3142, 36)
    assert real_train.y.shape == (3142,)
    assert real_train.n_positive == 403
    assert set(np.unique(real_train.y)) == {0, 1}
    assert len(real_train.names) == 36
    # the source provides 13 of SpreadAI's 18 canonical lines -> coverage 13/18
    assert real_train.coverage.min() == pytest.approx(13 / 18, abs=1e-9)


def test_labels_match_raw_status_column():
    records = iter_records("train")
    assert len(records) == 3142
    raw_failed = sum(1 for r in records if r["status_label"].strip().lower() == "failed")
    assert raw_failed == 403
    assert sum(label_of(r) for r in records) == raw_failed


def test_unknown_split_rejected():
    with pytest.raises(ValueError):
        iter_records("not-a-split")


# ------------------------------------------------- spreading a real statement


def test_spread_of_known_failed_company_shows_distress():
    # Find the real record for the worked example (cik C2, newest year FY2010):
    # negative equity, current ratio < 1, liabilities > assets, net loss.
    record = next(r for r in iter_records("train") if r["cik"] == "C2")
    statement, validation = spread_year(record, "3")
    bs = statement.balance_sheet

    # equity is the balancing item: assets - liabilities = 25088 - 29033 < 0
    assert statement.balance_sheet.total_equity == pytest.approx(25088.0 - 29033.0, abs=1.0)
    assert bs.total_equity < 0
    assert validation.balanced is True  # identity holds by construction

    from spreadai.ratios import compute_ratios

    ratios = compute_ratios(statement)
    assert ratios["current_ratio"] == pytest.approx(6838.0 / 8780.0, abs=1e-3)  # 0.779 < 1
    assert ratios["current_ratio"] < 1.0
    assert ratios["debt_to_assets"] == pytest.approx(29033.0 / 25088.0, abs=1e-3)  # > 1
    assert ratios["debt_to_assets"] > 1.0
    assert ratios["net_margin"] == pytest.approx(-471.0 / 22170.0, abs=1e-4)  # loss
    assert ratios["net_margin"] < 0


def test_round_trip_recovers_the_13_mapped_lines():
    record = iter_records("train")[0]
    from spreadai.extract.text_parser import parse_text

    extraction = parse_text(real_data.render_statement_text(record, "3"))
    # exactly the 13 canonical keys we populate should be found
    assert len(set(extraction.found_keys)) == 13
    assert extraction.statement.income_statement.revenue == float(record["3_total_revenue"])


# --------------------------------------------------- generalization + verdict


def test_pipeline_beats_baseline_on_held_out(real_train: RealDataset, real_test: RealDataset):
    result = run_benchmark(train=real_train, test=real_test)
    assert isinstance(result, BenchmarkResult)
    # real signal: clears chance comfortably on unseen years
    assert result.test_auc > 0.62
    assert result.test_auc > result.baseline_auc + 0.05
    assert result.test_average_precision > result.test_prevalence  # beats prevalence
    # generalizes: CV and held-out agree, so it is not overfit
    assert abs(result.cv_minus_test_gap) < AGREEMENT_TOLERANCE
    # both negative controls collapse to chance
    assert result.shuffled_label_cv_auc == pytest.approx(0.5, abs=0.07)
    assert result.scrambled_input_test_auc == pytest.approx(0.5, abs=0.07)
    assert result.verdict == "well-fit"


def test_verdict_discriminates_real_from_shuffled(real_train: RealDataset, real_test: RealDataset):
    # Real labels -> well-fit.
    good = run_benchmark(train=real_train, test=real_test)
    assert good.verdict == "well-fit"

    # Shuffle the labels of both splits -> the same pipeline must NOT be well-fit.
    rng = np.random.default_rng(1)
    ytr = real_train.y.copy()
    yte = real_test.y.copy()
    rng.shuffle(ytr)
    rng.shuffle(yte)
    shuffled_train = RealDataset(real_train.X, ytr, real_train.names,
                                 real_train.coverage, real_train.balanced)
    shuffled_test = RealDataset(real_test.X, yte, real_test.names,
                                real_test.coverage, real_test.balanced)
    bad = run_benchmark(train=shuffled_train, test=shuffled_test)
    assert bad.verdict != "well-fit"
    assert bad.test_auc < good.test_auc


def test_classify_fit_branches():
    base = dict(baseline_auc=0.5, shuffled_label_cv_auc=0.5, scrambled_input_test_auc=0.5)
    assert classify_fit(cv_auc_mean=0.70, test_auc=0.71, **base)[0] == "well-fit"
    assert classify_fit(cv_auc_mean=0.52, test_auc=0.52, **base)[0] == "underfit"
    assert classify_fit(cv_auc_mean=0.85, test_auc=0.62, **base)[0] == "overfit"
    leaking = dict(baseline_auc=0.5, shuffled_label_cv_auc=0.70, scrambled_input_test_auc=0.5)
    assert classify_fit(cv_auc_mean=0.70, test_auc=0.71, **leaking)[0] == "invalid"


def test_format_report_is_readable(real_train: RealDataset, real_test: RealDataset):
    text = format_report(run_benchmark(train=real_train, test=real_test))
    assert "VERDICT: WELL-FIT" in text
    assert "held-out ROC-AUC" in text
    assert "negative control" in text


# ----------------------------------------------------------- offline fetch


def _fake_archive_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        header = "cik,fyear,status_label\n"
        for split, name in SPLITS.items():
            zf.writestr(f"dataset_paper/{name}", header + f"C1,2010,{split}\n")
    return buf.getvalue()


class _Resp:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_fetch_retries_then_succeeds(monkeypatch, tmp_path):
    payload = _fake_archive_bytes()
    calls = {"n": 0}
    sleeps: list[float] = []

    def flaky_urlopen(url, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:  # fail twice, succeed on the third attempt
            raise OSError("transient network error")
        return _Resp(payload)

    monkeypatch.setattr(real_data, "urlopen", flaky_urlopen)
    written = fetch_american_bankruptcy(
        tmp_path, retries=4, backoff_base=2.0, sleep=sleeps.append
    )

    assert calls["n"] == 3
    assert sleeps == [1.0, 2.0]  # backoff_base**0, **1 for the two failures
    for split, name in SPLITS.items():
        assert written[split].exists()
        assert (tmp_path / name).read_text().endswith(f"C1,2010,{split}\n")
    # the freshly fetched snapshot is loadable as real records
    assert iter_records("train", data_dir=tmp_path)[0]["status_label"] == "train"


def test_fetch_raises_after_retries_exhausted(monkeypatch, tmp_path):
    calls = {"n": 0}

    def always_fails(url, timeout=None):
        calls["n"] += 1
        raise OSError("down")

    monkeypatch.setattr(real_data, "urlopen", always_fails)
    with pytest.raises(FetchError):
        fetch_american_bankruptcy(tmp_path, retries=3, sleep=lambda _s: None)
    assert calls["n"] == 3  # exactly `retries` attempts, no extra

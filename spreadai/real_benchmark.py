"""Validate SpreadAI's spreading pipeline on real financial statements.

This is the generalization proof for the real-data path. It takes the nine credit
ratios SpreadAI computes for each of three fiscal years (plus their trends) and asks
a single downstream question a credit desk actually cares about: *does this company
fail next year?* The features come straight out of SpreadAI's extractor + ratios, so
what is being validated is SpreadAI's output, not a separate feature set.

The report is built to make over/under-fitting impossible to hide:

* **Baseline** - a no-skill majority/prevalence classifier (ROC-AUC 0.5).
* **Cross-validation** - stratified k-fold on the training split, mean +/- std.
* **Held-out test** - the dataset's own later years (2016-2018), never seen in CV.
* **Train-vs-held-out gap** - reported, but the verdict is driven by CV<->held-out
  agreement, so a model that saturates on train is not mislabelled as overfit.
* **Negative controls** - shuffled labels *and* column-scrambled inputs. Both must
  collapse to chance; if they do not, the pipeline is leaking and the run is void.

Run it with ``python -m spreadai.real_benchmark``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .real_data import RealDataset, load_dataset

CHANCE_AUC = 0.5
# A run is only "well-fit" if the held-out AUC clears chance by this margin ...
SIGNAL_MARGIN = 0.05
# ... and CV and held-out AUC agree to within this tolerance.
AGREEMENT_TOLERANCE = 0.10
# A negative control must land inside this band around chance.
CONTROL_BAND = 0.07


def make_model(random_state: int = 0) -> Pipeline:
    """The downstream classifier: standardize, then L2 logistic regression.

    Linear and regularized on purpose - it cannot memorize the training set, so a
    large train-vs-held-out gap would be a real red flag rather than an artefact of
    model capacity. ``class_weight='balanced'`` handles the ~13% failure rate.
    """
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=5000,
                    class_weight="balanced",
                    C=1.0,
                    random_state=random_state,
                ),
            ),
        ]
    )


def _impute_clip(train: np.ndarray, *others: np.ndarray) -> list[np.ndarray]:
    """Median-impute NaNs and clip to the train 1st-99th percentile (fit on train)."""
    medians = np.nanmedian(train, axis=0)
    lo = np.nanpercentile(train, 1, axis=0)
    hi = np.nanpercentile(train, 99, axis=0)
    out = []
    for arr in (train, *others):
        arr = arr.copy()
        idx = np.where(~np.isfinite(arr))
        arr[idx] = np.take(medians, idx[1])
        out.append(np.clip(arr, lo, hi))
    return out


def _cv_auc(X: np.ndarray, y: np.ndarray, *, n_splits: int, random_state: int) -> np.ndarray:
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    scores = []
    for train_idx, val_idx in skf.split(X, y):
        model = make_model(random_state)
        model.fit(X[train_idx], y[train_idx])
        proba = model.predict_proba(X[val_idx])[:, 1]
        scores.append(roc_auc_score(y[val_idx], proba))
    return np.asarray(scores)


@dataclass
class BenchmarkResult:
    n_train: int
    n_test: int
    train_positives: int
    test_positives: int
    test_prevalence: float
    coverage_mean: float
    balanced_fraction: float
    baseline_auc: float
    baseline_test_balanced_acc: float
    cv_auc_mean: float
    cv_auc_std: float
    train_auc: float
    test_auc: float
    test_average_precision: float
    test_balanced_acc: float
    train_minus_test_gap: float
    cv_minus_test_gap: float
    shuffled_label_cv_auc: float
    scrambled_input_test_auc: float
    verdict: str
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def classify_fit(
    *,
    baseline_auc: float,
    cv_auc_mean: float,
    test_auc: float,
    shuffled_label_cv_auc: float,
    scrambled_input_test_auc: float,
) -> tuple[str, list[str]]:
    """Derive the over/under/well-fit verdict from the measured numbers.

    Rules (in order):

    1. If either negative control strays from chance, the pipeline leaks -> ``"invalid"``.
    2. If the held-out AUC does not clear chance by ``SIGNAL_MARGIN`` -> ``"underfit"``
       (the model learned nothing that transfers).
    3. If CV and held-out AUC disagree by more than ``AGREEMENT_TOLERANCE`` -> ``"overfit"``
       (it fit the training folds but not unseen years).
    4. Otherwise -> ``"well-fit"``.
    """
    reasons: list[str] = []
    control_ok = (
        abs(shuffled_label_cv_auc - CHANCE_AUC) <= CONTROL_BAND
        and abs(scrambled_input_test_auc - CHANCE_AUC) <= CONTROL_BAND
    )
    if not control_ok:
        reasons.append(
            f"negative control did not collapse to chance "
            f"(shuffled={shuffled_label_cv_auc:.3f}, scrambled={scrambled_input_test_auc:.3f})"
        )
        return "invalid", reasons

    if test_auc < baseline_auc + SIGNAL_MARGIN:
        reasons.append(
            f"held-out AUC {test_auc:.3f} does not clear baseline {baseline_auc:.3f} "
            f"by {SIGNAL_MARGIN}"
        )
        return "underfit", reasons

    gap = abs(cv_auc_mean - test_auc)
    if gap > AGREEMENT_TOLERANCE:
        reasons.append(
            f"CV AUC {cv_auc_mean:.3f} and held-out AUC {test_auc:.3f} disagree by "
            f"{gap:.3f} (> {AGREEMENT_TOLERANCE})"
        )
        return "overfit", reasons

    reasons.append(
        f"held-out AUC {test_auc:.3f} beats baseline {baseline_auc:.3f} and agrees with "
        f"CV {cv_auc_mean:.3f} (gap {gap:.3f}); controls at chance"
    )
    return "well-fit", reasons


def run_benchmark(
    *,
    train: RealDataset | None = None,
    test: RealDataset | None = None,
    n_splits: int = 5,
    random_state: int = 0,
) -> BenchmarkResult:
    """Spread the real train/test splits, fit the model, and score generalization."""
    if train is None:
        train = load_dataset("train")
    if test is None:
        test = load_dataset("test")

    Xtr, Xte = _impute_clip(train.X, test.X)
    ytr, yte = train.y, test.y

    # Baseline: constant predictor -> AUC is exactly chance; balanced accuracy is 0.5.
    baseline_auc = CHANCE_AUC
    baseline_balanced_acc = balanced_accuracy_score(yte, np.zeros_like(yte))

    cv = _cv_auc(Xtr, ytr, n_splits=n_splits, random_state=random_state)

    model = make_model(random_state)
    model.fit(Xtr, ytr)
    train_proba = model.predict_proba(Xtr)[:, 1]
    test_proba = model.predict_proba(Xte)[:, 1]
    train_auc = roc_auc_score(ytr, train_proba)
    test_auc = roc_auc_score(yte, test_proba)
    test_ap = average_precision_score(yte, test_proba)
    test_bacc = balanced_accuracy_score(yte, (test_proba >= 0.5).astype(int))

    # Negative control 1: destroy the label-feature relationship.
    rng = np.random.default_rng(random_state)
    y_shuffled = ytr.copy()
    rng.shuffle(y_shuffled)
    shuffled_cv = _cv_auc(Xtr, y_shuffled, n_splits=n_splits, random_state=random_state).mean()

    # Negative control 2: scramble each feature column independently (kills structure).
    Xtr_scr = Xtr.copy()
    Xte_scr = Xte.copy()
    for col in range(Xtr_scr.shape[1]):
        Xtr_scr[:, col] = rng.permutation(Xtr_scr[:, col])
        Xte_scr[:, col] = rng.permutation(Xte_scr[:, col])
    scr_model = make_model(random_state)
    scr_model.fit(Xtr_scr, ytr)
    scrambled_test_auc = roc_auc_score(yte, scr_model.predict_proba(Xte_scr)[:, 1])

    verdict, reasons = classify_fit(
        baseline_auc=baseline_auc,
        cv_auc_mean=float(cv.mean()),
        test_auc=float(test_auc),
        shuffled_label_cv_auc=float(shuffled_cv),
        scrambled_input_test_auc=float(scrambled_test_auc),
    )

    return BenchmarkResult(
        n_train=len(ytr),
        n_test=len(yte),
        train_positives=int(ytr.sum()),
        test_positives=int(yte.sum()),
        test_prevalence=float(yte.mean()),
        coverage_mean=float(test.coverage.mean()),
        balanced_fraction=float(test.balanced.mean()),
        baseline_auc=baseline_auc,
        baseline_test_balanced_acc=float(baseline_balanced_acc),
        cv_auc_mean=float(cv.mean()),
        cv_auc_std=float(cv.std()),
        train_auc=float(train_auc),
        test_auc=float(test_auc),
        test_average_precision=float(test_ap),
        test_balanced_acc=float(test_bacc),
        train_minus_test_gap=float(train_auc - test_auc),
        cv_minus_test_gap=float(cv.mean() - test_auc),
        shuffled_label_cv_auc=float(shuffled_cv),
        scrambled_input_test_auc=float(scrambled_test_auc),
        verdict=verdict,
        reasons=reasons,
    )


def format_report(result: BenchmarkResult) -> str:
    r = result
    lines = [
        "SpreadAI - real-data generalization benchmark",
        "American Bankruptcy dataset (U.S. public companies, 1999-2018)",
        "Task: predict next-year failure from SpreadAI's spread + ratios",
        "=" * 66,
        f"train records: {r.n_train:>6}  (failed: {r.train_positives})",
        f"test records:  {r.n_test:>6}  (failed: {r.test_positives}, "
        f"prevalence {r.test_prevalence:.3%})",
        f"extraction field coverage (test): {r.coverage_mean:.3f}",
        f"accounting identity balanced (test): {r.balanced_fraction:.3%}",
        "-" * 66,
        f"baseline (majority) ROC-AUC:      {r.baseline_auc:.4f}",
        f"baseline balanced accuracy:       {r.baseline_test_balanced_acc:.4f}",
        f"cross-val ROC-AUC (train):        {r.cv_auc_mean:.4f} +/- {r.cv_auc_std:.4f}",
        f"train ROC-AUC:                    {r.train_auc:.4f}",
        f"held-out ROC-AUC (2016-2018):     {r.test_auc:.4f}",
        f"held-out average precision:       {r.test_average_precision:.4f}  "
        f"(baseline {r.test_prevalence:.4f})",
        f"held-out balanced accuracy:       {r.test_balanced_acc:.4f}",
        f"train - held-out gap:             {r.train_minus_test_gap:+.4f}",
        f"CV - held-out gap:                {r.cv_minus_test_gap:+.4f}",
        "-" * 66,
        f"negative control, shuffled labels (CV AUC):   {r.shuffled_label_cv_auc:.4f}",
        f"negative control, scrambled inputs (test AUC): {r.scrambled_input_test_auc:.4f}",
        "-" * 66,
        f"VERDICT: {r.verdict.upper()}",
    ]
    lines += [f"  - {reason}" for reason in r.reasons]
    return "\n".join(lines)


def main() -> None:
    print(format_report(run_benchmark()))


if __name__ == "__main__":
    main()

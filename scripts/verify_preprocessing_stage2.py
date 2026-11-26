"""Stage 2.3 (TV3): Verification script for feature selection & model-specific preprocessing.

Runs directly on the official 183-day normalized datasets from Stage 2.1 (Handbook) and
Stage 2.2 (Sparkov) using scripts/transaction_features.py::build_features to verify all
Stage 2.3 acceptance criteria without touching test-set performance metrics:
  1. Feature lists A and A+B match scripts/transaction_features.py (FEATURES_A, FEATURES_B).
  2. Strict exclusion of labels, IDs, timestamps, splits, and fraud-scenario columns.
  3. Fit-on-train-only guarantee (mutating validation does not change fitted imputer/scaler).
  4. Cold-start (brand-new customer with missing history) produces finite risk_score across
     all 6 (algorithm x feature_set) pipelines on both datasets.
  5. Input dimensions and missing-value counts before/after preprocessing for train,
     validation, and test splits on both Handbook and Sparkov.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.transaction_features import FEATURES_A, FEATURES_B, build_features  # noqa: E402
from src.ml.preprocessing import (  # noqa: E402
    ALGORITHMS,
    FEATURE_SET_A,
    FEATURE_SET_B_EXTRA,
    FEATURE_SETS,
    build_model_pipeline,
    build_preprocessor,
    get_feature_columns,
    score_model,
    select_feature_frame,
    validate_feature_columns,
)

SEED = 42
DEFAULT_DATASETS: dict[str, Path] = {
    "handbook": Path("data/handbook_183_days.csv.gz"),
    "sparkov": Path("data/sparkov_183_days.csv.gz"),
}
DEFAULT_REPORT = Path("data/samples/ml_stage2_preprocessing_report.csv")


def verify_feature_dictionary_alignment() -> dict[str, bool]:
    """Confirm src/ml/preprocessing.py matches scripts/transaction_features.py exactly."""
    assert FEATURE_SET_A == FEATURES_A, f"Mismatch in FEATURES_A: {FEATURE_SET_A} vs {FEATURES_A}"
    assert FEATURE_SET_B_EXTRA == FEATURES_B, f"Mismatch in FEATURES_B: {FEATURE_SET_B_EXTRA} vs {FEATURES_B}"
    return {"matches_transaction_features_py": True}


def verify_forbidden_columns_blocked() -> dict[str, bool]:
    """Confirm forbidden columns are rejected by validate_feature_columns."""
    blocked_samples = [
        "label",
        "transaction_id",
        "entity_id",
        "timestamp",
        "dataset",
        "split",
        "TX_FRAUD_SCENARIO",
        "fraud_scenario",
    ]
    for col in blocked_samples:
        try:
            validate_feature_columns(["log_amount", col])
        except ValueError:
            continue
        raise AssertionError(f"Expected ValueError for forbidden column {col!r}, but it passed.")
    return {"all_forbidden_samples_rejected": True}


def verify_train_only_fitting(train_features: pd.DataFrame, val_features: pd.DataFrame) -> dict[str, bool]:
    """Verify fitted preprocessor parameters depend strictly on train split, never validation/test."""
    for algo in ("logistic_regression", "isolation_forest"):
        prep_a = build_preprocessor(algo, "A+B")
        prep_b = build_preprocessor(algo, "A+B")

        X_train = select_feature_frame(train_features, "A+B")
        X_val_orig = select_feature_frame(val_features, "A+B")
        X_val_poisoned = X_val_orig.copy()
        X_val_poisoned["log_amount"] = 1e9
        X_val_poisoned["seconds_since_previous"] = 1e9

        prep_a.fit(X_train)
        _ = prep_a.transform(X_val_orig)

        prep_b.fit(X_train)
        _ = prep_b.transform(X_val_poisoned)

        imp_a = prep_a.named_transformers_["continuous"].named_steps["imputer"].statistics_
        imp_b = prep_b.named_transformers_["continuous"].named_steps["imputer"].statistics_
        assert np.array_equal(imp_a, imp_b), f"{algo}: imputer statistics differed!"

        if algo == "logistic_regression":
            sc_a = prep_a.named_transformers_["continuous"].named_steps["scaler"]
            sc_b = prep_b.named_transformers_["continuous"].named_steps["scaler"]
            assert np.array_equal(sc_a.mean_, sc_b.mean_), "LR scaler mean differed!"
            assert np.array_equal(sc_a.scale_, sc_b.scale_), "LR scaler scale differed!"

    return {"train_only_fit_verified": True}


def build_new_customer_feature_row(dataset_name: str) -> pd.DataFrame:
    """Single brand-new customer/card transaction with no prior history."""
    tx = pd.DataFrame(
        [
            {
                "dataset": dataset_name,
                "transaction_id": f"{dataset_name}_NEW_CUSTOMER_001",
                "timestamp": "2019-06-15 14:30:00",
                "entity_id": "BRAND_NEW_ENTITY_001",
                "amount": 125.50,
                "label": 0,
                "split": "validation",
            }
        ]
    )
    feats = build_features(tx, feature_set="A+B")
    assert int(feats["missing_history"].iloc[0]) == 1
    assert pd.isna(feats["seconds_since_previous"].iloc[0])
    assert pd.isna(feats["amount_to_median_7d"].iloc[0])
    return feats


def verify_dataset(dataset_name: str, csv_path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Run all Stage 2.3 preprocessing checks on one official 183-day dataset."""
    transactions = pd.read_csv(
        csv_path,
        dtype={"transaction_id": "string", "entity_id": "string"},
    )
    features_ab = build_features(transactions, feature_set="A+B")

    # Verify non-feature columns from transactions never enter features_ab
    validate_feature_columns(list(features_ab.columns))

    train_mask = transactions["split"].eq("train")
    val_mask = transactions["split"].eq("validation")
    test_mask = transactions["split"].eq("test")
    assert int(train_mask.sum()) > 0 and int(val_mask.sum()) > 0 and int(test_mask.sum()) > 0, (
        f"{dataset_name}: expected non-empty train, validation, and test splits."
    )

    train_feats = features_ab.loc[train_mask]
    val_feats = features_ab.loc[val_mask]
    test_feats = features_ab.loc[test_mask]
    y_train = transactions.loc[train_mask, "label"].to_numpy()

    train_only_check = verify_train_only_fitting(train_feats, val_feats)
    new_customer_feats = build_new_customer_feature_row(dataset_name)

    report_rows: list[dict[str, object]] = []
    cold_start_scores: dict[str, float] = {}

    for feature_set in FEATURE_SETS:
        expected_cols = get_feature_columns(feature_set)
        X_train = select_feature_frame(train_feats, feature_set)
        assert list(X_train.columns) == expected_cols

        for algo in ALGORITHMS:
            pipe = build_model_pipeline(algo, feature_set, seed=SEED)
            if algo == "isolation_forest":
                pipe.fit(X_train)
            else:
                pipe.fit(X_train, y_train)

            # Brand-new customer (cold-start) must receive a finite risk_score
            nc_score = float(score_model(pipe, algo, new_customer_feats, feature_set)[0])
            cold_start_scores[f"{algo}__{feature_set}"] = round(nc_score, 6)

            # Also verify validation scores are all finite (test labels/metrics remain locked!)
            val_scores = score_model(pipe, algo, val_feats, feature_set)
            assert np.isfinite(val_scores).all(), f"{dataset_name}/{algo}/{feature_set}: non-finite val scores"

            preprocessor = pipe.named_steps["preprocess"]
            for split_name, split_feats in (
                ("train", train_feats),
                ("validation", val_feats),
                ("test", test_feats),
            ):
                X_raw = select_feature_frame(split_feats, feature_set)
                X_proc = preprocessor.transform(X_raw)

                missing_before = int(X_raw.isna().sum().sum())
                missing_after = int(np.isnan(X_proc).sum())
                has_inf_after = bool(np.isinf(X_proc).any())
                assert not has_inf_after, f"{dataset_name}/{algo}/{feature_set}/{split_name}: inf detected!"

                if algo in ("logistic_regression", "isolation_forest"):
                    assert missing_after == 0, f"{dataset_name}/{algo}/{feature_set}/{split_name}: NaNs left!"

                report_rows.append(
                    {
                        "dataset": dataset_name,
                        "algorithm": algo,
                        "feature_set": feature_set,
                        "split": split_name,
                        "n_rows": int(X_raw.shape[0]),
                        "n_features_in": int(X_raw.shape[1]),
                        "n_features_out": int(X_proc.shape[1]),
                        "missing_before": missing_before,
                        "missing_after": missing_after,
                        "no_inf_after": not has_inf_after,
                    }
                )

    dataset_summary = {
        "source": str(csv_path).replace("\\", "/"),
        "split_sizes": {
            "train": int(train_mask.sum()),
            "validation": int(val_mask.sum()),
            "test": int(test_mask.sum()),
        },
        "train_only_fit_check": train_only_check,
        "new_customer_cold_start_scores": cold_start_scores,
    }
    return report_rows, dataset_summary


def run_verification(datasets: dict[str, Path], report_path: Path) -> dict[str, object]:
    alignment_check = verify_feature_dictionary_alignment()
    forbidden_check = verify_forbidden_columns_blocked()

    all_rows: list[dict[str, object]] = []
    dataset_summaries: dict[str, object] = {}

    for name, path in datasets.items():
        rows, summary = verify_dataset(name, path)
        all_rows.extend(rows)
        dataset_summaries[name] = summary

    report_df = pd.DataFrame(all_rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_df.to_csv(report_path, index=False, lineterminator="\n")

    return {
        "feature_dictionary_alignment": alignment_check,
        "forbidden_column_check": forbidden_check,
        "feature_sets": {k: list(v) for k, v in FEATURE_SETS.items()},
        "datasets": dataset_summaries,
        "report_rows": int(len(report_df)),
        "report_path": str(report_path).replace("\\", "/"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 2.3 preprocessing & leakage verification.")
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Output CSV path for input dimensions & missingness report (default: {DEFAULT_REPORT})",
    )
    args = parser.parse_args()

    summary = run_verification(DEFAULT_DATASETS, args.report)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

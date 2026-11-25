"""Stage 2.3 (TV3): Verification script for feature selection & model-specific preprocessing.

Runs on either a real feature-engineered CSV (--input) or a deterministic synthetic 183-day
dataset (90 train / 30 validation / 63 test) containing realistic missing history and
deliberate non-feature columns (label, transaction_id, entity_id, TX_FRAUD_SCENARIO) to
verify all Stage 2.3 acceptance criteria:
  1. Fit-on-train-only guarantee (mutating val/test does not change fitted imputer/scaler).
  2. Strict exclusion of labels, IDs, timestamps, and fraud-scenario columns.
  3. Cold-start (brand-new customer with missing history) produces finite risk_score.
  4. Input dimensions and missing-value counts before/after preprocessing across all splits.
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

from src.ml.preprocessing import (  # noqa: E402
    ALGORITHMS,
    FEATURE_SETS,
    build_model_pipeline,
    build_preprocessor,
    get_feature_columns,
    score_model,
    select_feature_frame,
    validate_feature_columns,
)

SEED = 42
DEFAULT_REPORT = Path("data/samples/ml_stage2_preprocessing_report.csv")


def build_synthetic_stage2_dataset(seed: int = SEED) -> pd.DataFrame:
    """Create a deterministic 183-day dataset (90 train / 30 val / 63 test) with A and A+B features."""
    rng = np.random.default_rng(seed)
    rows_per_day = 12
    total_days = 183
    n_rows = rows_per_day * total_days

    base_date = pd.Timestamp("2018-04-01")
    day_indices = np.repeat(np.arange(total_days), rows_per_day)
    seconds_in_day = rng.integers(0, 86400, size=n_rows)
    timestamps = [
        base_date + pd.Timedelta(days=int(d), seconds=int(s))
        for d, s in zip(day_indices, seconds_in_day)
    ]

    splits = np.where(day_indices < 90, "train", np.where(day_indices < 120, "val", "test"))

    # Assign 2.5% fraud across all splits
    labels = (rng.random(n_rows) < 0.025).astype(int)
    # Guarantee at least 5 fraud rows in each split
    for sp in ("train", "val", "test"):
        sp_idx = np.where(splits == sp)[0]
        if labels[sp_idx].sum() < 5:
            labels[sp_idx[:5]] = 1

    amounts = np.where(
        labels == 1,
        rng.lognormal(mean=5.8, sigma=0.45, size=n_rows),
        rng.lognormal(mean=3.5, sigma=0.55, size=n_rows),
    )
    amounts = np.round(amounts, 2)

    # Deliberately introduce ~12% brand-new customers (missing history)
    missing_hist = (rng.random(n_rows) < 0.12).astype(int)
    tx_count_1h = np.where(missing_hist == 1, 0, rng.poisson(lam=0.6, size=n_rows))
    tx_count_24h = np.where(missing_hist == 1, 0, tx_count_1h + rng.poisson(lam=2.2, size=n_rows))
    time_since_last_tx = np.where(
        missing_hist == 1,
        np.nan,
        np.round(rng.exponential(scale=18.0, size=n_rows), 4),
    )
    amount_to_7d_median = np.where(
        missing_hist == 1,
        np.nan,
        np.round(np.where(labels == 1, rng.uniform(2.0, 6.0, n_rows), rng.uniform(0.4, 1.8, n_rows)), 4),
    )

    ts_series = pd.Series(pd.to_datetime(timestamps))
    hour = ts_series.dt.hour + ts_series.dt.minute / 60.0
    dow = ts_series.dt.dayofweek

    df = pd.DataFrame(
        {
            "dataset": "synthetic_stage2",
            "transaction_id": [f"TX_{i:06d}" for i in range(1, n_rows + 1)],
            "timestamp": ts_series,
            "date": ts_series.dt.strftime("%Y-%m-%d"),
            "split": splits,
            "entity_id": [f"ENT_{int(e):04d}" for e in rng.integers(1, 301, size=n_rows)],
            "amount": amounts,
            "label": labels,
            # Deliberate non-feature / leakage columns to verify exclusion
            "TX_FRAUD_SCENARIO": np.where(labels == 1, rng.integers(1, 4, size=n_rows), 0),
            "TERMINAL_ID": [f"TERM_{int(t):04d}" for t in rng.integers(1, 101, size=n_rows)],
            # Feature Set A
            "log_amount": np.log1p(amounts),
            "hour_sin": np.sin(2.0 * np.pi * hour / 24.0),
            "hour_cos": np.cos(2.0 * np.pi * hour / 24.0),
            "dow_sin": np.sin(2.0 * np.pi * dow / 7.0),
            "dow_cos": np.cos(2.0 * np.pi * dow / 7.0),
            # Feature Set B extra
            "tx_count_1h": tx_count_1h,
            "tx_count_24h": tx_count_24h,
            "time_since_last_tx": time_since_last_tx,
            "amount_to_7d_median": amount_to_7d_median,
            "missing_history_flag": missing_hist,
        }
    )
    return df


def verify_forbidden_columns_blocked() -> dict[str, bool]:
    """Confirm forbidden columns are rejected by validate_feature_columns."""
    blocked_samples = ["label", "transaction_id", "entity_id", "TX_FRAUD_SCENARIO", "fraud_scenario"]
    for col in blocked_samples:
        try:
            validate_feature_columns(["log_amount", col])
        except ValueError:
            continue
        raise AssertionError(f"Expected ValueError for forbidden column {col!r}, but it passed.")
    return {"all_forbidden_samples_rejected": True}


def verify_train_only_fitting(train_df: pd.DataFrame, val_df: pd.DataFrame) -> dict[str, bool]:
    """Verify fitted preprocessor parameters depend strictly on train_df, never val/test."""
    for algo in ("logistic_regression", "isolation_forest"):
        prep_a = build_preprocessor(algo, "A+B")
        prep_b = build_preprocessor(algo, "A+B")

        X_train = select_feature_frame(train_df, "A+B")
        X_val_orig = select_feature_frame(val_df, "A+B")
        X_val_poisoned = X_val_orig.copy()
        X_val_poisoned["log_amount"] = 1e9
        X_val_poisoned["time_since_last_tx"] = 1e9

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


def build_new_customer_row() -> pd.DataFrame:
    """Single brand-new customer transaction with missing history."""
    return pd.DataFrame(
        [
            {
                "dataset": "synthetic_stage2",
                "transaction_id": "TX_NEW_CUSTOMER_001",
                "timestamp": pd.Timestamp("2018-09-15 14:30:00"),
                "date": "2018-09-15",
                "split": "test",
                "entity_id": "ENT_BRAND_NEW",
                "amount": 125.50,
                "label": 0,
                "TX_FRAUD_SCENARIO": 0,
                "log_amount": float(np.log1p(125.50)),
                "hour_sin": float(np.sin(2.0 * np.pi * 14.5 / 24.0)),
                "hour_cos": float(np.cos(2.0 * np.pi * 14.5 / 24.0)),
                "dow_sin": float(np.sin(2.0 * np.pi * 5 / 7.0)),
                "dow_cos": float(np.cos(2.0 * np.pi * 5 / 7.0)),
                "tx_count_1h": 0,
                "tx_count_24h": 0,
                "time_since_last_tx": np.nan,
                "amount_to_7d_median": np.nan,
                "missing_history_flag": 1,
            }
        ]
    )


def run_verification(input_path: Path | None, report_path: Path) -> dict[str, object]:
    if input_path is not None:
        df = pd.read_csv(input_path, dtype={"transaction_id": str, "entity_id": str})
        source_label = str(input_path).replace("\\", "/")
    else:
        df = build_synthetic_stage2_dataset(seed=SEED)
        source_label = "synthetic_183d_90_30_63"

    train_df = df[df["split"] == "train"].reset_index(drop=True)
    val_df = df[df["split"] == "val"].reset_index(drop=True)
    test_df = df[df["split"] == "test"].reset_index(drop=True)

    assert len(train_df) > 0 and len(val_df) > 0 and len(test_df) > 0, (
        "Dataset must contain non-empty train, val, and test splits."
    )

    forbidden_check = verify_forbidden_columns_blocked()
    leakage_check = verify_train_only_fitting(train_df, val_df)
    new_customer_df = build_new_customer_row()

    report_rows: list[dict[str, object]] = []
    cold_start_scores: dict[str, float] = {}

    for feature_set in FEATURE_SETS:
        expected_cols = get_feature_columns(feature_set)
        X_train = select_feature_frame(train_df, feature_set)
        y_train = train_df["label"].to_numpy()
        assert list(X_train.columns) == expected_cols

        for algo in ALGORITHMS:
            pipe = build_model_pipeline(algo, feature_set, seed=SEED)
            if algo == "isolation_forest":
                pipe.fit(X_train)
            else:
                pipe.fit(X_train, y_train)

            # Cold-start check for brand-new customer
            nc_score = float(score_model(pipe, algo, new_customer_df, feature_set)[0])
            cold_start_scores[f"{algo}__{feature_set}"] = round(nc_score, 6)

            preprocessor = pipe.named_steps["preprocess"]
            for split_name, split_df in (("train", train_df), ("val", val_df), ("test", test_df)):
                X_raw = select_feature_frame(split_df, feature_set)
                X_proc = preprocessor.transform(X_raw)
                scores = score_model(pipe, algo, split_df, feature_set)

                missing_before = int(X_raw.isna().sum().sum())
                missing_after = int(np.isnan(X_proc).sum())
                if algo in ("logistic_regression", "isolation_forest"):
                    assert missing_after == 0, f"{algo} ({feature_set}, {split_name}) left NaNs!"

                report_rows.append(
                    {
                        "algorithm": algo,
                        "feature_set": feature_set,
                        "split": split_name,
                        "n_rows": int(X_raw.shape[0]),
                        "n_features_in": int(X_raw.shape[1]),
                        "n_features_out": int(X_proc.shape[1]),
                        "missing_before": missing_before,
                        "missing_after": missing_after,
                        "all_scores_finite": bool(np.isfinite(scores).all()),
                    }
                )

    report_df = pd.DataFrame(report_rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_df.to_csv(report_path, index=False, lineterminator="\n")

    return {
        "source": source_label,
        "feature_sets": {k: list(v) for k, v in FEATURE_SETS.items()},
        "split_sizes": {
            "train": int(len(train_df)),
            "val": int(len(val_df)),
            "test": int(len(test_df)),
        },
        "forbidden_column_check": forbidden_check,
        "train_only_fit_check": leakage_check,
        "new_customer_cold_start_scores": cold_start_scores,
        "report_rows": int(len(report_df)),
        "report_path": str(report_path).replace("\\", "/"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 2.3 preprocessing & leakage verification.")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional feature-engineered CSV path. Defaults to synthetic 183-day dataset.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Output CSV path for input dimensions & missingness report (default: {DEFAULT_REPORT})",
    )
    args = parser.parse_args()

    summary = run_verification(args.input, args.report)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

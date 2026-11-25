"""Stage 1.3 (TV3): Smoke test for Isolation Forest, Logistic Regression, and HistGradientBoosting.

Generates a small deterministic two-class transaction table matching the shared schema,
trains all three candidate algorithms, verifies finite 1-to-1 risk scores and Isolation Forest
anomaly score direction (higher risk_score = higher fraud/anomaly priority), and writes the
sample score table to CSV.
"""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEED = 42
DEFAULT_OUTPUT = Path("data/samples/ml_stage1_sample_scores.csv")
FEATURE_COLS = ["log_amount", "hour_sin", "hour_cos", "dow_sin", "dow_cos"]


def build_synthetic_transactions(n_rows: int = 200, seed: int = SEED) -> pd.DataFrame:
    """Create a deterministic two-class dataset matching the shared transaction schema."""
    rng = np.random.default_rng(seed)

    # 10% fraud spread across both train (first 70%) and eval (last 30%) windows
    labels = np.zeros(n_rows, dtype=int)
    train_end = int(n_rows * 0.7)
    fraud_train_idx = rng.choice(np.arange(0, train_end), size=14, replace=False)
    fraud_eval_idx = rng.choice(np.arange(train_end, n_rows), size=6, replace=False)
    labels[fraud_train_idx] = 1
    labels[fraud_eval_idx] = 1

    base_ts = pd.Timestamp("2018-04-01 00:00:00")
    offsets_sec = np.sort(rng.integers(0, 5 * 86400, size=n_rows))
    timestamps = [base_ts + pd.Timedelta(seconds=int(s)) for s in offsets_sec]

    # Normal transactions: moderate amounts; fraud transactions: noticeably higher amounts
    normal_amounts = rng.lognormal(mean=3.4, sigma=0.45, size=n_rows)
    fraud_amounts = rng.lognormal(mean=6.2, sigma=0.35, size=n_rows)
    amounts = np.where(labels == 1, fraud_amounts, normal_amounts)
    amounts = np.round(amounts, 2)

    entity_ids = [f"CUST_{int(cid):04d}" for cid in rng.integers(1, 51, size=n_rows)]
    tx_ids = [f"SYN_{i:05d}" for i in range(1, n_rows + 1)]

    df = pd.DataFrame(
        {
            "dataset": "synthetic_stage1",
            "transaction_id": tx_ids,
            "timestamp": pd.to_datetime(timestamps),
            "entity_id": entity_ids,
            "amount": amounts,
            "label": labels,
        }
    )
    return df


def add_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute minimal cyclic time + log-amount features (Feature Set A prototype)."""
    out = df.copy()
    hour = out["timestamp"].dt.hour + out["timestamp"].dt.minute / 60.0
    dow = out["timestamp"].dt.dayofweek

    out["log_amount"] = np.log1p(out["amount"])
    out["hour_sin"] = np.sin(2.0 * np.pi * hour / 24.0)
    out["hour_cos"] = np.cos(2.0 * np.pi * hour / 24.0)
    out["dow_sin"] = np.sin(2.0 * np.pi * dow / 7.0)
    out["dow_cos"] = np.cos(2.0 * np.pi * dow / 7.0)
    return out


def verify_isolation_forest_direction(
    model: IsolationForest, X_train: pd.DataFrame, eval_df: pd.DataFrame, eval_scores: np.ndarray
) -> dict[str, float | bool]:
    """Verify that Isolation Forest risk_score = -decision_function ranks anomalies higher."""
    normal_probe = pd.DataFrame([X_train.median().to_dict()], columns=FEATURE_COLS)
    extreme_outlier = pd.DataFrame(
        [
            {
                "log_amount": float(X_train["log_amount"].max() + 5.0),
                "hour_sin": 0.0,
                "hour_cos": 1.0,
                "dow_sin": 0.0,
                "dow_cos": 1.0,
            }
        ],
        columns=FEATURE_COLS,
    )

    raw_normal = float(model.decision_function(normal_probe)[0])
    raw_outlier = float(model.decision_function(extreme_outlier)[0])
    risk_normal = -raw_normal
    risk_outlier = -raw_outlier

    if not (raw_outlier < raw_normal and risk_outlier > risk_normal):
        raise AssertionError(
            "Isolation Forest direction check failed: "
            f"raw_outlier={raw_outlier:.6f}, raw_normal={raw_normal:.6f}, "
            f"risk_outlier={risk_outlier:.6f}, risk_normal={risk_normal:.6f}"
        )

    fraud_mean = float(eval_scores[eval_df["label"].to_numpy() == 1].mean())
    normal_mean = float(eval_scores[eval_df["label"].to_numpy() == 0].mean())
    if not (fraud_mean > normal_mean):
        raise AssertionError(
            "Isolation Forest eval separation check failed: "
            f"fraud_mean={fraud_mean:.6f} <= normal_mean={normal_mean:.6f}"
        )

    return {
        "raw_decision_normal_probe": round(raw_normal, 6),
        "raw_decision_extreme_outlier": round(raw_outlier, 6),
        "risk_score_normal_probe": round(risk_normal, 6),
        "risk_score_extreme_outlier": round(risk_outlier, 6),
        "eval_mean_risk_label_0": round(normal_mean, 6),
        "eval_mean_risk_label_1": round(fraud_mean, 6),
        "higher_risk_means_more_anomalous": True,
    }


def run_smoke_test(output_path: Path) -> dict[str, object]:
    raw_df = build_synthetic_transactions(n_rows=200, seed=SEED)
    feat_df = add_basic_features(raw_df)

    split_idx = int(len(feat_df) * 0.7)
    train_df = feat_df.iloc[:split_idx].reset_index(drop=True)
    eval_df = feat_df.iloc[split_idx:].reset_index(drop=True)

    # Confirm both classes exist in train and eval
    assert set(train_df["label"].unique()) == {0, 1}, "Train split must contain both classes 0 and 1."
    assert set(eval_df["label"].unique()) == {0, 1}, "Eval split must contain both classes 0 and 1."

    X_train = train_df[FEATURE_COLS]
    y_train = train_df["label"].to_numpy()
    X_eval = eval_df[FEATURE_COLS]

    # 1. Isolation Forest (unsupervised; negate decision_function so higher = more anomalous)
    iso_forest = IsolationForest(max_samples=min(256, len(X_train)), random_state=SEED)
    iso_forest.fit(X_train)
    iso_scores = -iso_forest.decision_function(X_eval)
    if_check = verify_isolation_forest_direction(iso_forest, X_train, eval_df, iso_scores)

    # 2. Logistic Regression (supervised; standardized inputs)
    log_reg = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(C=1.0, max_iter=1000, random_state=SEED)),
        ]
    )
    log_reg.fit(X_train, y_train)
    lr_scores = log_reg.predict_proba(X_eval)[:, 1]

    # 3. HistGradientBoosting (supervised)
    hgb = HistGradientBoostingClassifier(max_leaf_nodes=15, random_state=SEED)
    hgb.fit(X_train, y_train)
    hgb_scores = hgb.predict_proba(X_eval)[:, 1]

    model_scores = {
        "isolation_forest": iso_scores,
        "logistic_regression": lr_scores,
        "hist_gradient_boosting": hgb_scores,
    }

    records: list[pd.DataFrame] = []
    model_summaries: dict[str, dict[str, float | int | bool]] = {}

    for algo_name, scores in model_scores.items():
        scores = np.asarray(scores, dtype=float)
        assert scores.ndim == 1 and len(scores) == len(eval_df), (
            f"{algo_name}: expected {len(eval_df)} scores, got shape {scores.shape}"
        )
        assert np.isfinite(scores).all(), f"{algo_name}: found non-finite risk_score values"

        part = eval_df[["dataset", "transaction_id", "timestamp", "entity_id", "amount", "label"]].copy()
        part["date"] = part["timestamp"].dt.strftime("%Y-%m-%d")
        part["timestamp"] = part["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        part["algorithm"] = algo_name
        part["risk_score"] = np.round(scores, 6)
        part = part[
            ["dataset", "date", "transaction_id", "timestamp", "entity_id", "amount", "label", "algorithm", "risk_score"]
        ]
        records.append(part)

        model_summaries[algo_name] = {
            "n_scores": int(len(scores)),
            "all_finite": bool(np.isfinite(scores).all()),
            "min_score": round(float(scores.min()), 6),
            "median_score": round(float(np.median(scores)), 6),
            "max_score": round(float(scores.max()), 6),
        }

    score_table = pd.concat(records, ignore_index=True)
    assert not score_table.duplicated(subset=["transaction_id", "algorithm"]).any(), (
        "Duplicate (transaction_id, algorithm) rows detected."
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    score_table.to_csv(output_path, index=False, lineterminator="\n")

    summary = {
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "data": {
            "total_rows": int(len(feat_df)),
            "train_rows": int(len(train_df)),
            "train_fraud": int(train_df["label"].sum()),
            "eval_rows": int(len(eval_df)),
            "eval_fraud": int(eval_df["label"].sum()),
            "output_rows": int(len(score_table)),
            "output_path": str(output_path).replace("\\", "/"),
        },
        "models": model_summaries,
        "isolation_forest_direction_check": if_check,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1.3 smoke test for the three ML algorithms.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path for sample scores (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    summary = run_smoke_test(args.output)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

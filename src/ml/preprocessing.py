"""Stage 2.3 (TV3): Feature definitions, leakage guards, and model-specific preprocessing.

Aligns directly with scripts/transaction_features.py (FEATURES_A, FEATURES_B), enforces
strict exclusion of labels, identifiers, timestamps, splits, and fraud-scenario columns,
and builds model-specific scikit-learn preprocessing pipelines fit strictly on train data.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

ALGORITHMS = (
    "isolation_forest",
    "logistic_regression",
    "hist_gradient_boosting",
)

# Feature Set A: matches scripts/transaction_features.py FEATURES_A
FEATURE_SET_A: tuple[str, ...] = (
    "log_amount",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
)

# Feature Set B extra: matches scripts/transaction_features.py FEATURES_B
FEATURE_SET_B_EXTRA: tuple[str, ...] = (
    "count_1h",
    "count_24h",
    "seconds_since_previous",
    "amount_to_median_7d",
    "missing_history",
)

FEATURE_SET_AB: tuple[str, ...] = FEATURE_SET_A + FEATURE_SET_B_EXTRA

FEATURE_SETS: dict[str, tuple[str, ...]] = {
    "A": FEATURE_SET_A,
    "A+B": FEATURE_SET_AB,
}

BINARY_FLAG_COLUMNS: frozenset[str] = frozenset({"missing_history"})

# Columns that must NEVER enter model features (checked case-insensitively)
FORBIDDEN_COLUMNS: frozenset[str] = frozenset(
    {
        "dataset",
        "transaction_id",
        "tx_id",
        "timestamp",
        "tx_datetime",
        "date",
        "split",
        "entity_id",
        "customer_id",
        "card_id",
        "cc_num",
        "terminal_id",
        "label",
        "tx_fraud",
        "is_fraud",
        "tx_fraud_scenario",
        "fraud_scenario",
        "scenario",
    }
)


def _to_float64(X: pd.DataFrame | np.ndarray) -> np.ndarray:
    return np.asarray(X, dtype=np.float64)


def get_feature_columns(
    feature_set: str,
    column_mapping: Mapping[str, str] | None = None,
) -> list[str]:
    """Return ordered column names for Feature Set 'A' or 'A+B'."""
    if feature_set not in FEATURE_SETS:
        raise ValueError(f"Unknown feature_set {feature_set!r}. Expected one of {sorted(FEATURE_SETS)}.")

    canonical_cols = FEATURE_SETS[feature_set]
    if column_mapping:
        cols = [column_mapping.get(col, col) for col in canonical_cols]
    else:
        cols = list(canonical_cols)

    validate_feature_columns(cols)
    return cols


def validate_feature_columns(columns: Sequence[str]) -> None:
    """Reject any label, identifier, timestamp, split, or fraud-scenario column."""
    if not columns:
        raise ValueError("Feature column list cannot be empty.")

    if len(set(columns)) != len(columns):
        raise ValueError(f"Duplicate feature columns detected: {list(columns)}")

    leaked = [col for col in columns if col.strip().lower() in FORBIDDEN_COLUMNS]
    if leaked:
        raise ValueError(f"Forbidden non-feature columns detected in model inputs: {leaked}")


def select_feature_frame(
    df: pd.DataFrame,
    feature_set: str,
    column_mapping: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Strictly select and validate allowed feature columns from a DataFrame."""
    cols = get_feature_columns(feature_set, column_mapping=column_mapping)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns for feature_set={feature_set!r}: {missing}")

    X = df.loc[:, cols].copy()
    for col in cols:
        X[col] = pd.to_numeric(X[col], errors="coerce").astype("float64")
    return X


def build_preprocessor(
    algorithm: str,
    feature_set: str,
    column_mapping: Mapping[str, str] | None = None,
) -> ColumnTransformer:
    """Build model-specific preprocessing pipeline (fit strictly on train split).

    - logistic_regression:
        continuous -> median imputation + StandardScaler
        missing_history -> constant(1.0) imputation (kept unscaled 0/1)
    - isolation_forest:
        continuous -> median imputation (tree-based, scale-invariant)
        missing_history -> constant(1.0) imputation
    - hist_gradient_boosting:
        continuous -> float64 passthrough (native NaN handling in HGB)
        missing_history -> constant(1.0) imputation
    """
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm {algorithm!r}. Expected one of {ALGORITHMS}.")

    cols = get_feature_columns(feature_set, column_mapping=column_mapping)
    flag_names = {
        column_mapping.get(name, name) if column_mapping else name
        for name in BINARY_FLAG_COLUMNS
    }
    continuous_cols = [c for c in cols if c not in flag_names]
    binary_cols = [c for c in cols if c in flag_names]

    transformers: list[tuple[str, Any, list[str]]] = []

    if algorithm == "logistic_regression":
        cont_pipe = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )
        transformers.append(("continuous", cont_pipe, continuous_cols))
    elif algorithm == "isolation_forest":
        cont_pipe = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
            ]
        )
        transformers.append(("continuous", cont_pipe, continuous_cols))
    elif algorithm == "hist_gradient_boosting":
        cont_pipe = Pipeline(
            [
                ("to_float", FunctionTransformer(_to_float64, validate=False)),
            ]
        )
        transformers.append(("continuous", cont_pipe, continuous_cols))

    if binary_cols:
        flag_pipe = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="constant", fill_value=1.0)),
            ]
        )
        transformers.append(("binary_flags", flag_pipe, binary_cols))

    return ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        sparse_threshold=0.0,
    )


def build_estimator(
    algorithm: str,
    params: Mapping[str, Any] | None = None,
    seed: int = 42,
) -> Any:
    """Instantiate one of the three candidate algorithms with fixed seed."""
    cfg = dict(params or {})

    if algorithm == "isolation_forest":
        return IsolationForest(
            max_samples=cfg.get("max_samples", 256),
            random_state=seed,
        )
    if algorithm == "logistic_regression":
        return LogisticRegression(
            C=cfg.get("C", 1.0),
            max_iter=cfg.get("max_iter", 1000),
            random_state=seed,
        )
    if algorithm == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(
            max_leaf_nodes=cfg.get("max_leaf_nodes", 15),
            random_state=seed,
        )

    raise ValueError(f"Unknown algorithm {algorithm!r}. Expected one of {ALGORITHMS}.")


def build_model_pipeline(
    algorithm: str,
    feature_set: str,
    params: Mapping[str, Any] | None = None,
    seed: int = 42,
    column_mapping: Mapping[str, str] | None = None,
) -> Pipeline:
    """Combine model-specific preprocessor and estimator into a single Pipeline."""
    preprocessor = build_preprocessor(algorithm, feature_set, column_mapping=column_mapping)
    estimator = build_estimator(algorithm, params=params, seed=seed)
    return Pipeline(
        [
            ("preprocess", preprocessor),
            ("model", estimator),
        ]
    )


def score_model(
    fitted_pipeline: Pipeline,
    algorithm: str,
    df: pd.DataFrame,
    feature_set: str,
    column_mapping: Mapping[str, str] | None = None,
) -> np.ndarray:
    """Produce 1D finite risk_score array where higher score = higher fraud/anomaly priority."""
    X = select_feature_frame(df, feature_set, column_mapping=column_mapping)

    if algorithm == "isolation_forest":
        scores = -fitted_pipeline.decision_function(X)
    elif algorithm in ("logistic_regression", "hist_gradient_boosting"):
        scores = fitted_pipeline.predict_proba(X)[:, 1]
    else:
        raise ValueError(f"Unknown algorithm {algorithm!r}.")

    scores = np.asarray(scores, dtype=np.float64)
    if scores.ndim != 1 or len(scores) != len(df):
        raise AssertionError(
            f"{algorithm} ({feature_set}): expected {len(df)} 1D scores, got shape {scores.shape}"
        )
    if not np.isfinite(scores).all():
        raise AssertionError(f"{algorithm} ({feature_set}): non-finite risk_score detected.")
    return scores

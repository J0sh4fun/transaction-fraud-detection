"""Stage 3.3 (TV3): Train and score all 24 validation candidates on Handbook and Sparkov.

Runs all 24 candidate combinations (2 datasets x 2 feature sets x 3 algorithms x 2
hyperparameter values) with fixed seed=42:
  - isolation_forest: max_samples in {256, 1024}
  - logistic_regression: C in {0.1, 1.0}
  - hist_gradient_boosting: max_leaf_nodes in {15, 31}

Training uses strictly the 90-day train split (split == "train") and scoring uses the
30-day validation split (split == "validation"). The 63-day test split is never touched.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.transaction_features import build_features  # noqa: E402
from src.ml.preprocessing import (  # noqa: E402
    build_model_pipeline,
    score_model,
    select_feature_frame,
)

SEED = 42

DATASETS: dict[str, Path] = {
    "handbook": Path("data/handbook_183_days.csv.gz"),
    "sparkov": Path("data/sparkov_183_days.csv.gz"),
}

FEATURE_SETS: tuple[str, ...] = ("A", "A+B")

FULL_GRID: tuple[tuple[str, str, list[Any]], ...] = (
    ("isolation_forest", "max_samples", [256, 1024]),
    ("logistic_regression", "C", [0.1, 1.0]),
    ("hist_gradient_boosting", "max_leaf_nodes", [15, 31]),
)

REDUCED_GRID: tuple[tuple[str, str, list[Any]], ...] = (
    ("isolation_forest", "max_samples", [256]),
    ("logistic_regression", "C", [1.0]),
    ("hist_gradient_boosting", "max_leaf_nodes", [15]),
)

DEFAULT_SCORES_DIR = Path("data/validation_scores")
DEFAULT_LOG_PATH = Path("data/stage3_validation_runs.csv")


def format_config_tag(param_name: str, param_value: Any) -> str:
    if isinstance(param_value, float) and param_value.is_integer():
        val_str = str(int(param_value))
    else:
        val_str = str(param_value)
    return f"{param_name}={val_str}"


def format_file_slug(dataset: str, algorithm: str, feature_set: str, param_name: str, param_value: Any) -> str:
    fs_slug = feature_set.lower().replace("+", "_plus_")
    val_slug = str(param_value).replace(".", "p")
    return f"{dataset}__{algorithm}__{fs_slug}__{param_name}_{val_slug}.csv.gz"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_validation_experiments(
    scores_dir: Path,
    log_path: Path,
    reduced: bool = False,
    seed: int = SEED,
) -> dict[str, object]:
    grid = REDUCED_GRID if reduced else FULL_GRID
    scores_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    run_records: list[dict[str, object]] = []
    dataset_val_stats: dict[str, dict[str, object]] = {}

    for dataset_name, csv_path in DATASETS.items():
        print(f"[stage3] Loading {dataset_name} from {csv_path} ...", flush=True)
        t_load = time.perf_counter()
        transactions = pd.read_csv(
            csv_path,
            dtype={"transaction_id": "string", "entity_id": "string"},
        )
        # Compute A+B features on full chronological table so validation rows inherit train history
        features_ab = build_features(transactions, feature_set="A+B")
        load_sec = time.perf_counter() - t_load

        train_mask = transactions["split"].eq("train")
        val_mask = transactions["split"].eq("validation")

        train_feats = features_ab.loc[train_mask].reset_index(drop=True)
        val_feats = features_ab.loc[val_mask].reset_index(drop=True)
        y_train = transactions.loc[train_mask, "label"].to_numpy(dtype=np.int64)

        val_meta = transactions.loc[
            val_mask, ["dataset", "transaction_id", "timestamp", "label"]
        ].reset_index(drop=True)
        val_meta["date"] = pd.to_datetime(val_meta["timestamp"], format="ISO8601").dt.strftime("%Y-%m-%d")
        val_meta["label"] = val_meta["label"].astype(int)

        assert not val_meta["transaction_id"].duplicated().any(), (
            f"{dataset_name}: duplicate transaction_id in validation split!"
        )
        n_train = int(len(train_feats))
        n_val = int(len(val_meta))
        n_val_days = int(val_meta["date"].nunique())
        assert n_val_days == 30, f"{dataset_name}: expected 30 validation days, got {n_val_days}"

        dataset_val_stats[dataset_name] = {
            "train_rows": n_train,
            "validation_rows": n_val,
            "validation_days": n_val_days,
            "validation_fraud": int(val_meta["label"].sum()),
            "feature_build_seconds": round(load_sec, 3),
        }
        print(
            f"[stage3] {dataset_name}: train={n_train:,}, val={n_val:,} ({n_val_days} days), "
            f"features built in {load_sec:.2f}s",
            flush=True,
        )

        # Pre-select feature matrices once per feature_set
        X_train_by_fs = {fs: select_feature_frame(train_feats, fs) for fs in FEATURE_SETS}

        for feature_set in FEATURE_SETS:
            X_train = X_train_by_fs[feature_set]

            for algorithm, param_name, param_values in grid:
                for param_value in param_values:
                    config_tag = format_config_tag(param_name, param_value)
                    params = {param_name: param_value}
                    pipe = build_model_pipeline(algorithm, feature_set, params=params, seed=seed)

                    t0 = time.perf_counter()
                    if algorithm == "isolation_forest":
                        pipe.fit(X_train)
                    else:
                        pipe.fit(X_train, y_train)
                    train_seconds = time.perf_counter() - t0

                    t1 = time.perf_counter()
                    scores = score_model(pipe, algorithm, val_feats, feature_set)
                    score_seconds = time.perf_counter() - t1

                    assert len(scores) == n_val, f"Expected {n_val} scores, got {len(scores)}"
                    assert np.isfinite(scores).all(), f"Non-finite scores in {dataset_name}/{algorithm}/{config_tag}"

                    out_df = pd.DataFrame(
                        {
                            "dataset": val_meta["dataset"],
                            "date": val_meta["date"],
                            "transaction_id": val_meta["transaction_id"],
                            "timestamp": val_meta["timestamp"],
                            "label": val_meta["label"],
                            "algorithm": algorithm,
                            "feature_set": feature_set,
                            "config": config_tag,
                            "risk_score": np.round(scores, 6),
                        }
                    )

                    filename = format_file_slug(dataset_name, algorithm, feature_set, param_name, param_value)
                    out_path = scores_dir / filename
                    with out_path.open("wb") as raw_f:
                        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_f, compresslevel=6, mtime=0) as gz_raw:
                            with io.TextIOWrapper(gz_raw, encoding="utf-8", newline="") as gz:
                                out_df.to_csv(gz, index=False, lineterminator="\n")

                    record = {
                        "run_id": f"{dataset_name}|{algorithm}|{feature_set}|{config_tag}",
                        "dataset": dataset_name,
                        "algorithm": algorithm,
                        "feature_set": feature_set,
                        "config": config_tag,
                        "param_name": param_name,
                        "param_value": param_value,
                        "seed": seed,
                        "mode": "reduced" if reduced else "full",
                        "train_rows": n_train,
                        "validation_rows": n_val,
                        "validation_days": n_val_days,
                        "train_seconds": round(train_seconds, 3),
                        "score_seconds": round(score_seconds, 3),
                        "total_seconds": round(train_seconds + score_seconds, 3),
                        "min_score": round(float(scores.min()), 6),
                        "median_score": round(float(np.median(scores)), 6),
                        "max_score": round(float(scores.max()), 6),
                        "all_finite": True,
                        "score_file": str(out_path).replace("\\", "/"),
                        "score_file_sha256": sha256_file(out_path),
                    }
                    run_records.append(record)
                    print(
                        f"  done {record['run_id']}: train={train_seconds:.2f}s, "
                        f"score={score_seconds:.2f}s -> {out_path.name}",
                        flush=True,
                    )

    log_df = pd.DataFrame(run_records)
    expected_runs = 12 if reduced else 24
    assert len(log_df) == expected_runs, f"Expected {expected_runs} runs, got {len(log_df)}"
    log_df.to_csv(log_path, index=False, lineterminator="\n")

    return {
        "mode": "reduced" if reduced else "full",
        "total_runs": int(len(log_df)),
        "seed": seed,
        "datasets": dataset_val_stats,
        "log_path": str(log_path).replace("\\", "/"),
        "scores_dir": str(scores_dir).replace("\\", "/"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 3.3: Run all 24 validation candidates.")
    parser.add_argument(
        "--scores-dir",
        type=Path,
        default=DEFAULT_SCORES_DIR,
        help=f"Directory to store per-candidate validation score CSV.gz files (default: {DEFAULT_SCORES_DIR})",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help=f"Output CSV path for the 24-run experiment log (default: {DEFAULT_LOG_PATH})",
    )
    parser.add_argument(
        "--reduced",
        action="store_true",
        help="Run reduced fallback grid (256, C=1, 15 leaves) instead of all 24 candidates.",
    )
    args = parser.parse_args()

    summary = run_validation_experiments(args.scores_dir, args.log, reduced=args.reduced, seed=SEED)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

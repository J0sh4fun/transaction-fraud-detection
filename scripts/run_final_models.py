"""Stage 4.3 & 5.3 (TV3): Retrain locked 12 configurations and score target window.

Supports two explicit execution modes:
  - --mode dry-run (Stage 4.3): Exercises the exact retrain + score pipeline on a
    historical window strictly inside train + validation (first 113 days train ->
    last 7 days validation). Never reads or scores the 63-day test split.
  - --mode test (Stage 5.3): Retrains the 12 locked configurations on all 120 days
    (train + validation) and scores all 63 days of split == "test". Requires
    --confirm-stage4-approved to prevent accidental premature test evaluation.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.transaction_features import build_features  # noqa: E402
from src.ml.preprocessing import (  # noqa: E402
    build_model_pipeline,
    score_model,
    select_feature_frame,
)

DEFAULT_CONFIG = Path("configs/final_models_stage4.json")
DEFAULT_DRY_RUN_SCORES_DIR = Path("data/samples/stage4_dry_run_scores")
DEFAULT_DRY_RUN_LOG = Path("data/stage4_dry_run_log.csv")
DEFAULT_TEST_SCORES_DIR = Path("data/test_scores")
DEFAULT_TEST_LOG = Path("data/stage5_test_runs.csv")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def current_git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except Exception:
        return "unknown"


def format_file_slug(
    dataset: str,
    algorithm: str,
    feature_set: str,
    param_name: str,
    param_value: Any,
    prefix: str = "",
) -> str:
    fs_slug = feature_set.lower().replace("+", "_plus_")
    val_str = str(int(param_value)) if isinstance(param_value, float) and param_value.is_integer() else str(param_value)
    val_slug = val_str.replace(".", "p")
    stem = f"{dataset}__{algorithm}__{fs_slug}__{param_name}_{val_slug}.csv.gz"
    return f"{prefix}{stem}" if prefix else stem


def verify_config_matches_stage3_selection(config_data: dict[str, Any]) -> None:
    """Ensure the 12 locked models match data/selected_configurations_stage3.csv verbatim."""
    selection_path = REPO_ROOT / config_data["locked_from"]
    sel_df = pd.read_csv(selection_path)
    models = config_data["models"]
    assert len(models) == 12, f"Expected 12 locked configurations, got {len(models)}"
    assert len(sel_df) == 12, f"Expected 12 rows in {selection_path}, got {len(sel_df)}"

    expected_map: dict[tuple[str, str, str], tuple[str, float, int]] = {}
    for row in sel_df.itertuples(index=False):
        expected_map[(row.dataset, row.algorithm, row.feature_set)] = (
            str(row.parameter_name),
            float(row.parameter_value),
            int(row.seed),
        )

    seen: set[tuple[str, str, str]] = set()
    for m in models:
        key = (m["dataset"], m["algorithm"], m["feature_set"])
        assert key not in seen, f"Duplicate locked model key: {key}"
        seen.add(key)
        assert key in expected_map, f"Unexpected locked model key: {key}"
        exp_param, exp_val, exp_seed = expected_map[key]
        assert m["parameter_name"] == exp_param, f"Parameter name mismatch for {key}"
        assert float(m["parameter_value"]) == exp_val, f"Parameter value mismatch for {key}"
        assert int(m["seed"]) == exp_seed, f"Seed mismatch for {key}"


def run_locked_pipeline(
    config_path: Path,
    mode: str,
    dataset_filter: str,
    scores_dir: Path,
    log_path: Path,
    confirm_stage4_approved: bool = False,
) -> dict[str, object]:
    if mode == "test" and not confirm_stage4_approved:
        raise SystemExit(
            "Refusing to run --mode test without --confirm-stage4-approved. "
            "Per PLAN.md, Stage 5.3 may only run after 4.1-4.4 are all approved."
        )

    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    verify_config_matches_stage3_selection(config_data)

    policy = config_data["window_policy"]
    models_by_dataset: dict[str, list[dict[str, Any]]] = {}
    for m in config_data["models"]:
        if dataset_filter != "all" and m["dataset"] != dataset_filter:
            continue
        models_by_dataset.setdefault(m["dataset"], []).append(m)

    if not models_by_dataset:
        raise ValueError(f"No locked models matched dataset={dataset_filter!r}")

    scores_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    run_records: list[dict[str, object]] = []
    dataset_summaries: dict[str, dict[str, object]] = {}

    for dataset_name, model_specs in models_by_dataset.items():
        ds_info = config_data["datasets"][dataset_name]
        csv_path = Path(ds_info["path"])
        print(f"[{mode}] Loading {dataset_name} from {csv_path} ...", flush=True)
        t_load = time.perf_counter()
        transactions = pd.read_csv(
            csv_path,
            dtype={"transaction_id": "string", "entity_id": "string"},
        )
        # Compute A+B features on full chronological table so score window inherits prior history
        features_ab = build_features(transactions, feature_set="A+B")
        load_sec = time.perf_counter() - t_load

        tx_dates = pd.to_datetime(transactions["timestamp"], format="ISO8601").dt.strftime("%Y-%m-%d")

        if mode == "dry-run":
            # Strictly inside train + validation (never touch split == "test")
            allowed_mask = transactions["split"].isin(policy["dry_run_allowed_splits"])
            allowed_days = sorted(tx_dates.loc[allowed_mask].unique())
            n_train_days = int(policy["dry_run_train_days"])
            n_score_days = int(policy["dry_run_score_days"])
            assert len(allowed_days) == n_train_days + n_score_days, (
                f"{dataset_name}: expected {n_train_days + n_score_days} train+val days, got {len(allowed_days)}"
            )
            train_days = set(allowed_days[:n_train_days])
            score_days = set(allowed_days[n_train_days:])

            train_mask = allowed_mask & tx_dates.isin(train_days)
            score_mask = allowed_mask & tx_dates.isin(score_days)
            assert not transactions.loc[train_mask, "split"].eq("test").any(), "Test leaked into dry-run train!"
            assert not transactions.loc[score_mask, "split"].eq("test").any(), "Test leaked into dry-run score!"
            expected_score_days = n_score_days
        else:
            # Final Stage 5.3: 120 days (train + validation) -> 63 days (test)
            train_mask = transactions["split"].isin(policy["final_train_splits"])
            score_mask = transactions["split"].eq(policy["final_score_split"])
            expected_score_days = int(policy["final_score_days"])

        train_feats = features_ab.loc[train_mask].reset_index(drop=True)
        score_feats = features_ab.loc[score_mask].reset_index(drop=True)
        y_train = transactions.loc[train_mask, "label"].to_numpy(dtype=np.int64)

        score_meta = transactions.loc[
            score_mask, ["dataset", "transaction_id", "timestamp", "label"]
        ].reset_index(drop=True)
        score_meta["date"] = tx_dates.loc[score_mask].reset_index(drop=True)
        score_meta["label"] = score_meta["label"].astype(int)

        actual_train_days = int(tx_dates.loc[train_mask].nunique())
        actual_score_days = int(score_meta["date"].nunique())
        assert actual_score_days == expected_score_days, (
            f"{dataset_name}: expected {expected_score_days} score days, got {actual_score_days}"
        )
        assert not score_meta["transaction_id"].duplicated().any(), (
            f"{dataset_name}: duplicate transaction_id in score window!"
        )

        train_date_min = str(tx_dates.loc[train_mask].min())
        train_date_max = str(tx_dates.loc[train_mask].max())
        score_date_min = str(score_meta["date"].min())
        score_date_max = str(score_meta["date"].max())
        assert train_date_max < score_date_min, (
            f"{dataset_name}: temporal overlap {train_date_max} >= {score_date_min}"
        )

        dataset_summaries[dataset_name] = {
            "train_days": actual_train_days,
            "train_range": f"{train_date_min}..{train_date_max}",
            "train_rows": int(len(train_feats)),
            "score_days": actual_score_days,
            "score_range": f"{score_date_min}..{score_date_max}",
            "score_rows": int(len(score_meta)),
            "feature_build_seconds": round(load_sec, 3),
        }
        print(
            f"[{mode}] {dataset_name}: train={len(train_feats):,} ({actual_train_days}d: "
            f"{train_date_min}..{train_date_max}), score={len(score_meta):,} "
            f"({actual_score_days}d: {score_date_min}..{score_date_max})",
            flush=True,
        )

        X_train_by_fs = {
            fs: select_feature_frame(train_feats, fs)
            for fs in sorted({m["feature_set"] for m in model_specs})
        }

        for spec in model_specs:
            algo = spec["algorithm"]
            fs = spec["feature_set"]
            param_name = spec["parameter_name"]
            param_value = spec["parameter_value"]
            seed = int(spec["seed"])
            config_tag = spec["config"]

            X_train = X_train_by_fs[fs]
            pipe = build_model_pipeline(algo, fs, params={param_name: param_value}, seed=seed)

            t0 = time.perf_counter()
            if algo == "isolation_forest":
                pipe.fit(X_train)
            else:
                pipe.fit(X_train, y_train)
            train_seconds = time.perf_counter() - t0

            t1 = time.perf_counter()
            scores = score_model(pipe, algo, score_feats, fs)
            score_seconds = time.perf_counter() - t1

            assert len(scores) == len(score_meta)
            assert np.isfinite(scores).all()

            out_df = pd.DataFrame(
                {
                    "dataset": score_meta["dataset"],
                    "date": score_meta["date"],
                    "transaction_id": score_meta["transaction_id"],
                    "timestamp": score_meta["timestamp"],
                    "label": score_meta["label"],
                    "algorithm": algo,
                    "feature_set": fs,
                    "config": config_tag,
                    "risk_score": np.round(scores, 6),
                }
            )

            prefix = "dryrun__" if mode == "dry-run" else ""
            filename = format_file_slug(dataset_name, algo, fs, param_name, param_value, prefix=prefix)
            out_path = scores_dir / filename
            with out_path.open("wb") as raw_f:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw_f, compresslevel=6, mtime=0) as gz_raw:
                    with io.TextIOWrapper(gz_raw, encoding="utf-8", newline="") as gz:
                        out_df.to_csv(gz, index=False, lineterminator="\n")

            record = {
                "run_id": f"{dataset_name}|{algo}|{fs}|{config_tag}",
                "mode": mode,
                "dataset": dataset_name,
                "algorithm": algo,
                "feature_set": fs,
                "config": config_tag,
                "parameter_name": param_name,
                "parameter_value": param_value,
                "seed": seed,
                "train_days": actual_train_days,
                "train_range": f"{train_date_min}..{train_date_max}",
                "train_rows": int(len(train_feats)),
                "score_days": actual_score_days,
                "score_range": f"{score_date_min}..{score_date_max}",
                "score_rows": int(len(score_meta)),
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
    log_df.to_csv(log_path, index=False, lineterminator="\n")

    return {
        "mode": mode,
        "dataset_filter": dataset_filter,
        "total_runs": int(len(log_df)),
        "config_path": str(config_path).replace("\\", "/"),
        "config_sha256": sha256_file(config_path),
        "git_commit": current_git_commit(),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "datasets": dataset_summaries,
        "log_path": str(log_path).replace("\\", "/"),
        "scores_dir": str(scores_dir).replace("\\", "/"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 4.3/5.3: Retrain locked 12 models and score.")
    parser.add_argument(
        "--mode",
        choices=("dry-run", "test"),
        default="dry-run",
        help="dry-run: historical 113d->7d window inside train+val (Stage 4.3); test: 120d->63d (Stage 5.3).",
    )
    parser.add_argument(
        "--dataset",
        choices=("all", "handbook", "sparkov"),
        default="all",
        help="Run for both datasets or one dataset at a time (default: all).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"Locked configuration JSON path (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--scores-dir",
        type=Path,
        default=None,
        help="Output directory for score .csv.gz files (auto-selected by mode if omitted).",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Output CSV path for run log (auto-selected by mode if omitted).",
    )
    parser.add_argument(
        "--confirm-stage4-approved",
        action="store_true",
        help="Required safety flag for --mode test after Stage 4 (4.1-4.4) is fully approved.",
    )
    args = parser.parse_args()

    scores_dir = args.scores_dir or (
        DEFAULT_DRY_RUN_SCORES_DIR if args.mode == "dry-run" else DEFAULT_TEST_SCORES_DIR
    )
    log_path = args.log or (DEFAULT_DRY_RUN_LOG if args.mode == "dry-run" else DEFAULT_TEST_LOG)

    summary = run_locked_pipeline(
        config_path=args.config,
        mode=args.mode,
        dataset_filter=args.dataset,
        scores_dir=scores_dir,
        log_path=log_path,
        confirm_stage4_approved=args.confirm_stage4_approved,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

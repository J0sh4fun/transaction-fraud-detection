import argparse
import csv
import gzip
import hashlib
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from evaluate_alerts_stage2 import evaluate_alerts
from rank_amount_baseline import transaction_day


DATASETS = ("handbook", "sparkov")
FEATURE_SETS = ("A", "A+B")
CANDIDATES = {
    "isolation_forest": ("max_samples", (Decimal("256"), Decimal("1024"))),
    "logistic_regression": ("C", (Decimal("0.1"), Decimal("1"))),
    "hist_gradient_boosting": ("max_leaf_nodes", (Decimal("15"), Decimal("31"))),
}
K = 50
VALIDATION_DAYS = 30
RUN_FIELDS = (
    "dataset", "algorithm", "feature_set", "config", "param_name", "param_value", "seed",
    "mode", "validation_rows", "validation_days", "train_seconds", "score_seconds",
    "score_file", "score_file_sha256",
)
SCORE_FIELDS = (
    "dataset", "date", "transaction_id", "timestamp", "label", "algorithm",
    "feature_set", "config", "risk_score",
)


def csv_rows(path, required_columns):
    open_csv = gzip.open if path.suffix == ".gz" else open
    with open_csv(path, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(required_columns).difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: missing columns {', '.join(sorted(missing))}")
        yield from reader


def load_validation(path, dataset):
    fields = ("dataset", "transaction_id", "timestamp", "amount", "label", "split")
    transactions = {}
    days = set()
    for row in csv_rows(path, fields):
        if row["split"] != "validation":
            continue
        transaction_id = row["transaction_id"]
        if row["dataset"] != dataset or not transaction_id or transaction_id in transactions:
            raise ValueError(f"{path}: invalid or duplicate validation ID {transaction_id!r}")
        row["date"] = transaction_day(row)
        days.add(row["date"])
        transactions[transaction_id] = row
    if len(days) != VALIDATION_DAYS:
        raise ValueError(f"{path}: expected {VALIDATION_DAYS} validation days, found {len(days)}")
    return transactions


def period_metrics(rows, score_column="risk_score"):
    period, = (row for row in evaluate_alerts(rows, score_column) if row["scope"] == "period" and row["k"] == K)
    return {
        "validation_days": period["days"],
        "validation_rows": period["transactions"],
        "fraud_total": period["fraud_total"],
        "alerts_at_50": period["alerts"],
        "fraud_found_at_50": period["true_positives"],
        "fraud_found_per_day_at_50": period["true_positives_per_day"],
        "precision_at_50": period["precision"],
        "recall_at_50": period["recall"],
    }


def read_runs(tv3_root):
    expected = {
        (dataset, algorithm, feature_set, value)
        for dataset in DATASETS
        for algorithm, (_, values) in CANDIDATES.items()
        for feature_set in FEATURE_SETS
        for value in values
    }
    runs = {}
    for run in csv_rows(tv3_root / "data/stage3_validation_runs.csv", RUN_FIELDS):
        dataset, algorithm, features = (run[field] for field in ("dataset", "algorithm", "feature_set"))
        value = Decimal(run["param_value"])
        key = (dataset, algorithm, features, value)
        if key not in expected or key in runs:
            raise ValueError(f"Unexpected or duplicate run: {key}")
        name, _, config_value = run["config"].partition("=")
        if name != CANDIDATES[algorithm][0] or name != run["param_name"] or Decimal(config_value) != value:
            raise ValueError(f"Inconsistent config for {key}")
        if run["seed"] != "42" or run["mode"] != "full":
            raise ValueError(f"Expected a full run with seed 42 for {key}")
        for field in ("train_seconds", "score_seconds"):
            seconds = Decimal(run[field])
            if not seconds.is_finite() or seconds < 0:
                raise ValueError(f"Invalid {field} for {key}")
        score_dir = (tv3_root / "data/validation_scores").resolve()
        score_path = (tv3_root / run["score_file"]).resolve()
        if score_path.parent != score_dir:
            raise ValueError(f"Score file must be in {score_dir}: {score_path}")
        runs[key] = (run, score_path)
    if set(runs) != expected:
        raise ValueError(f"Missing validation runs: {sorted(expected - runs.keys())}")
    return runs


def checked_score_rows(path, run, validation):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != run["score_file_sha256"]:
        raise ValueError(f"{path}: SHA-256 does not match the run log")
    if int(run["validation_rows"]) != len(validation) or int(run["validation_days"]) != VALIDATION_DAYS:
        raise ValueError(f"{path}: run log does not match the validation split")

    run_fields = ("dataset", "algorithm", "feature_set", "config")
    expected_run = tuple(run[field] for field in run_fields)
    count = 0
    for row in csv_rows(path, SCORE_FIELDS):
        transaction_id = row["transaction_id"]
        original = validation.get(transaction_id)
        if tuple(row[field] for field in run_fields) != expected_run:
            raise ValueError(f"{path}: wrong run metadata for ID {transaction_id!r}")
        if original is None or any(row[field] != original[field] for field in ("date", "timestamp", "label")):
            raise ValueError(f"{path}: ID {transaction_id!r} does not match the official validation split")
        count += 1
        yield row
    # The stage 2 evaluator rejects duplicate IDs and non-finite scores.
    if count != len(validation):
        raise ValueError(f"{path}: expected {len(validation)} unique scores, found {count}")


def build_scorecard(validation_root, tv3_root):
    runs = read_runs(tv3_root)
    scorecard = []
    for dataset in DATASETS:
        validation = load_validation(validation_root / "data" / f"{dataset}_183_days.csv.gz", dataset)
        baseline = period_metrics(validation.values(), "amount")
        scorecard.append({
            "dataset": dataset, "algorithm": "amount_baseline", "feature_set": "",
            "config": "amount", "parameter_name": "", "parameter_value": "", "seed": "",
            "train_seconds": "", "score_seconds": "", "score_file": "",
            **baseline, "fraud_delta_vs_baseline_at_50": 0,
        })
        for (source, algorithm, features, value), (run, score_path) in sorted(runs.items()):
            if source != dataset:
                continue
            try:
                metrics = period_metrics(checked_score_rows(score_path, run, validation))
            except (ValueError, InvalidOperation) as error:
                raise ValueError(f"{run['score_file']}: {error}") from error
            scorecard.append({
                "dataset": dataset, "algorithm": algorithm, "feature_set": features,
                "config": run["config"], "parameter_name": run["param_name"],
                "parameter_value": format(value.normalize(), "f"), "seed": run["seed"],
                "train_seconds": run["train_seconds"], "score_seconds": run["score_seconds"],
                "score_file": run["score_file"], **metrics,
                "fraud_delta_vs_baseline_at_50": metrics["fraud_found_at_50"] - baseline["fraud_found_at_50"],
            })
        del validation
    return scorecard


def pick_configurations(scorecard):
    groups = defaultdict(list)
    for row in scorecard:
        if row["algorithm"] != "amount_baseline":
            key = (row["dataset"], row["algorithm"], row["feature_set"])
            groups[key].append(row)

    selected = []
    for _, candidates in sorted(groups.items()):
        winner, runner_up = sorted(
            candidates,
            key=lambda row: (-row["fraud_found_at_50"], Decimal(row["parameter_value"])),
        )
        tied = winner["fraud_found_at_50"] == runner_up["fraud_found_at_50"]
        selected.append({
            **winner,
            "alternative_parameter_value": runner_up["parameter_value"],
            "alternative_fraud_found_at_50": runner_up["fraud_found_at_50"],
            "selection_reason": "tie_smaller_parameter" if tied else "higher_fraud_found_per_day",
        })
    return selected


def write_table(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Audit TV3 runs and select stage 3 configurations at top 50 per day.")
    parser.add_argument("--tv3-root", type=Path, default=root, help="Checkout containing TV3's run log and score files")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for the scorecard and selections")
    args = parser.parse_args()
    try:
        scorecard = build_scorecard(root, args.tv3_root)
        selected = pick_configurations(scorecard)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_table(args.output_dir / "validation_scorecard_stage3.csv", scorecard)
        write_table(args.output_dir / "selected_configurations_stage3.csv", selected)
    except (OSError, ValueError, InvalidOperation, TypeError) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")
    print(f"Checked {len(scorecard) - len(DATASETS)} runs and selected {len(selected)} configurations.")


if __name__ == "__main__":
    main()

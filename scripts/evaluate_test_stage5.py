import argparse
import csv
import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from evaluate_alerts_stage2 import BUDGETS, evaluate_alerts
from evaluate_validation_stage3 import SCORE_FIELDS, csv_rows, write_table
from rank_amount_baseline import transaction_day


TEST_DAYS = 63
IDENTITY = ("dataset", "algorithm", "feature_set", "config", "seed")
RUN_FIELDS = (*IDENTITY, "mode", "train_days", "score_days", "score_range", "score_rows",
              "score_file", "score_file_sha256", "parameter_name", "parameter_value")
ALGORITHM_NAMES = {
    "amount_baseline": "Đối chứng số tiền", "hist_gradient_boosting": "HistGradientBoosting",
    "isolation_forest": "Isolation Forest", "logistic_regression": "Logistic Regression",
}


def identity(row):
    return tuple(str(row[field]) for field in IDENTITY)


def verify_hash(path, expected):
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError(f"SHA-256 does not match: {path}")


def read_inputs(root):
    config = json.loads((root / "configs/final_models_stage4.json").read_text(encoding="utf-8"))
    template = list(csv_rows(root / "data/test_results_template_stage4.csv", (*IDENTITY, "score_column")))
    model_rows = [row for row in template if row["score_column"] == "risk_score"]
    locked_models = {identity(row): row for row in config["models"]}
    if len(model_rows) != len(locked_models) or {identity(row) for row in model_rows} != locked_models.keys():
        raise ValueError("Template does not match locked model configurations")
    if len(template) != 14 or any(
        sum(row["dataset"] == dataset and row["algorithm"] == "amount_baseline"
            and row["score_column"] == "amount" for row in template) != 1
        for dataset in config["datasets"]
    ):
        raise ValueError("Expected 12 models and an amount baseline for each dataset")

    runs = {}
    for row in csv_rows(root / "data/stage5_test_runs.csv", RUN_FIELDS):
        key = identity(row)
        locked = locked_models.get(key)
        if locked is None or key in runs or row["mode"] != "test" or row["train_days"] != "120":
            raise ValueError(f"Unexpected or duplicate test run: {key}")
        if (row["parameter_name"], Decimal(row["parameter_value"])) != (
            locked["parameter_name"], Decimal(str(locked["parameter_value"])),
        ):
            raise ValueError(f"Run parameters do not match the locked configuration: {key}")
        runs[key] = row
    if runs.keys() != locked_models.keys():
        raise ValueError("The test run log does not cover all locked configurations")
    return config, template, runs


def load_test(root, dataset, reference):
    path = root / reference["path"]
    verify_hash(path, reference["sha256"])
    fields = ("dataset", "transaction_id", "timestamp", "amount", "label", "split")
    transactions = {}
    days = set()
    for row in csv_rows(path, fields):
        if row["split"] != "test":
            continue
        transaction_id = row["transaction_id"]
        if row["dataset"] != dataset or not transaction_id or transaction_id in transactions:
            raise ValueError(f"Invalid or duplicate test ID in {dataset}: {transaction_id!r}")
        row["date"] = transaction_day(row)
        del row["split"]
        transactions[transaction_id] = row
        days.add(row["date"])
    if len(days) != TEST_DAYS or (date.fromisoformat(max(days)) - date.fromisoformat(min(days))).days != TEST_DAYS - 1:
        raise ValueError(f"{dataset}: expected {TEST_DAYS} consecutive test dates")
    return transactions, sorted(days)


def checked_scores(root, run, transactions, days):
    path = root / run["score_file"]
    verify_hash(path, run["score_file_sha256"])
    if (int(run["score_rows"]), int(run["score_days"]), run["score_range"]) != (
        len(transactions), len(days), f"{days[0]}..{days[-1]}",
    ):
        raise ValueError(f"Logged score coverage does not match the test split: {path}")
    meta = ("dataset", "algorithm", "feature_set", "config")
    expected = tuple(run[field] for field in meta)
    count = 0
    for row in csv_rows(path, SCORE_FIELDS):
        original = transactions.get(row["transaction_id"])
        if original is None or any(row[field] != original[field] for field in ("date", "timestamp", "label")):
            raise ValueError(f"{path}: invalid test ID or metadata {row['transaction_id']!r}")
        if tuple(row[field] for field in meta) != expected:
            raise ValueError(f"{path}: row metadata differs from the run log")
        count += 1
        yield row
    # evaluate_alerts checks unique normalized IDs and finite scores as it consumes the stream.
    if count != len(transactions):
        raise ValueError(f"{path}: expected {len(transactions)} scores, found {count}")


def summarize(root):
    config, template, runs = read_inputs(root)
    results, weeks, audit = [], [], []
    for dataset, reference in config["datasets"].items():
        transactions, days = load_test(root, dataset, reference)
        for row in (r for r in template if r["dataset"] == dataset):
            score_column = row["score_column"]
            rows = transactions.values() if score_column == "amount" else checked_scores(root, runs[identity(row)], transactions, days)
            metrics = evaluate_alerts(rows, score_column)
            totals = {m["k"]: m for m in metrics if m["scope"] == "period"}
            daily = {m["date"]: m for m in metrics if m["scope"] == "day" and m["k"] == 50}
            if sorted(daily) != days or set(totals) != set(BUDGETS):
                raise ValueError(f"Incomplete test metrics for {identity(row)}")
            for total in totals.values():
                if not 0 <= total["true_positives"] <= min(total["alerts"], total["fraud_total"]):
                    raise ValueError(f"Invalid count of detected fraud for {identity(row)}")
            at_50 = totals[50]
            results.append({
                **row, "test_days": at_50["days"], "fraud_total": at_50["fraud_total"], "alerts_at_50": at_50["alerts"],
                **{f"fraud_found_at_{k}": totals[k]["true_positives"] for k in BUDGETS},
                "fraud_found_per_day_at_50": at_50["true_positives_per_day"],
                "precision_at_50": at_50["precision"], "recall_at_50": at_50["recall"],
                "extra_fraud_at_51_to_100": totals[100]["true_positives"] - at_50["true_positives"],
            })
            model = {field: row[field] for field in IDENTITY}
            for start in range(0, TEST_DAYS, 7):
                dates = days[start:start + 7]
                found = sum(daily[day]["true_positives"] for day in dates)
                weeks.append({**model, "week": start // 7 + 1, "from": dates[0], "through": dates[-1],
                              "fraud_found_at_50": found, "fraud_found_per_day_at_50": found / len(dates)})
            sample = daily[days[0]]
            audit.append({**model, "date": days[0], "transactions": sample["transactions"],
                          "fraud_total": sample["fraud_total"], "alerts_at_50": sample["alerts"],
                          "fraud_found_at_50": sample["true_positives"]})
        del transactions
    return results, weeks, audit


def plot_weekly(path, weeks):
    from matplotlib.figure import Figure

    figure = Figure(figsize=(13, 5.3), layout="constrained")
    colors = {"amount_baseline": "#353c46", "hist_gradient_boosting": "#17769c",
              "isolation_forest": "#b3581c", "logistic_regression": "#277653"}
    for axis, dataset in zip(figure.subplots(1, 2), ("handbook", "sparkov"), strict=True):
        per_model = {}
        for row in weeks:
            if row["dataset"] == dataset:
                per_model.setdefault((row["algorithm"], row["feature_set"]), []).append(row)
        for (algorithm, features), values in per_model.items():
            label = f"{ALGORITHM_NAMES[algorithm]} {features}".strip()
            axis.plot([v["week"] for v in values], [v["fraud_found_per_day_at_50"] for v in values],
                      label=label, color=colors[algorithm], linestyle={"": ":", "A": "--", "A+B": "-"}[features],
                      marker="o" if features == "A+B" else None, markersize=4, linewidth=1.7)
        axis.set(title=dataset.capitalize(), xlabel="Tuần test", ylabel="Ca gian lận phát hiện / ngày",
                 xticks=range(1, 10), ylim=(0, None))
        axis.grid(axis="y", alpha=0.25)
    handles, labels = figure.axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside lower center", ncols=4, frameon=False, fontsize=9)
    figure.suptitle("Phát hiện gian lận theo tuần với 50 lượt rà soát mỗi ngày", fontsize=15)
    figure.savefig(path, dpi=180, facecolor="white")


def main():
    parser = argparse.ArgumentParser(description="Evaluate 63 test days using the locked stage 4 protocol.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for the CSVs and weekly chart")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    results, weeks, audit = summarize(root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_table(args.output_dir / "test_results_stage5.csv", results)
    write_table(args.output_dir / "test_weekly_stage5.csv", weeks)
    plot_weekly(args.output_dir / "test_weekly_stage5.png", weeks)
    print("Validated 12 model score files and evaluated 14 runs over 63 test days.")
    print("First test day cross-check (dataset, algorithm, features, date, alerts, fraud detected):")
    for row in audit:
        print(*(row[k] for k in ("dataset", "algorithm", "feature_set", "date", "alerts_at_50", "fraud_found_at_50")))


if __name__ == "__main__":
    main()

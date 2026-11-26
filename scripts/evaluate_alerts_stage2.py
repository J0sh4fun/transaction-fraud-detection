import argparse
import csv
from collections import defaultdict
from decimal import InvalidOperation
from pathlib import Path

from rank_amount_baseline import transaction_day, transaction_rank_key


BUDGETS = (10, 25, 50, 100)
COLUMNS = (
    "dataset", "algorithm", "scope", "date", "k", "days", "transactions",
    "fraud_total", "alerts", "true_positives", "true_positives_per_day", "precision", "recall",
)


def evaluate_alerts(transactions, score_column="risk_score"):
    groups = defaultdict(lambda: defaultdict(list))
    seen = set()
    for row in transactions:
        dataset = row["dataset"]
        algorithm = row.get("algorithm", "model") if score_column == "risk_score" else "amount_baseline"
        rank_key = transaction_rank_key(row, score_column)
        key = (dataset, algorithm, rank_key[1])
        label = row["label"]
        if key in seen:
            raise ValueError(f"Duplicate transaction for dataset and algorithm: {key!r}")
        if not rank_key[0].is_finite() or label not in ("0", "1"):
            raise ValueError(f"Expected a finite score and binary label for {key!r}")
        seen.add(key)
        groups[dataset, algorithm][transaction_day(row)].append((rank_key, int(label)))

    results = []
    for (dataset, algorithm), by_day in sorted(groups.items()):
        period_totals = {k: [0, 0, 0, 0] for k in BUDGETS}
        for day, rows in sorted(by_day.items()):
            labels = [label for _, label in sorted(rows)]
            fraud_total = sum(labels)
            for k in BUDGETS:
                selected = labels[:k]
                counts = (len(labels), fraud_total, len(selected), sum(selected))
                results.append(metric_row(dataset, algorithm, day, k, 1, counts))
                for index, count in enumerate(counts):
                    period_totals[k][index] += count
        for k, totals in period_totals.items():
            results.append(metric_row(dataset, algorithm, "", k, len(by_day), totals))
    return results


def metric_row(dataset, algorithm, day, k, days, counts):
    transactions, fraud_total, alerts, true_positives = counts
    return {
        "dataset": dataset, "algorithm": algorithm, "scope": "day" if day else "period",
        "date": day, "k": k, "days": days, "transactions": transactions,
        "fraud_total": fraud_total, "alerts": alerts, "true_positives": true_positives,
        "true_positives_per_day": true_positives / days,
        "precision": true_positives / alerts if alerts else 0.0,
        "recall": true_positives / fraud_total if fraud_total else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate daily top-K fraud alerts from a CSV.")
    parser.add_argument("input", type=Path, help="Transaction CSV with scores and labels")
    parser.add_argument("output", type=Path, help="Output CSV with daily and period metrics")
    parser.add_argument("--score-column", choices=("risk_score", "amount"), default="risk_score")
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("input and output must be different files")

    required = {"dataset", "transaction_id", "timestamp", "label", args.score_column}
    with args.input.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = required.difference(reader.fieldnames or ())
        if missing:
            parser.error(f"missing input column(s): {', '.join(sorted(missing))}")
        try:
            results = evaluate_alerts(reader, args.score_column)
        except (TypeError, ValueError, InvalidOperation) as error:
            parser.error(str(error))
    if not results:
        parser.error("input contains no transactions")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    main()

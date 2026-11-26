import argparse
import csv
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path


OUTPUT_COLUMNS = ("dataset", "date", "transaction_id", "amount", "rank", "label")


def amount_rank_key(row):
    transaction_id = row["transaction_id"]
    if row["dataset"] == "handbook":
        transaction_id = int(transaction_id)
    return -Decimal(row["amount"]), transaction_id


def top_alerts_by_day(transactions, k=50):
    if k < 1:
        raise ValueError("k must be at least 1")

    by_day = defaultdict(list)
    for row in transactions:
        day = datetime.fromisoformat(row["timestamp"]).date().isoformat()
        by_day[row["dataset"], day].append(row)

    for (dataset, day), rows in sorted(by_day.items()):
        ranked = sorted(rows, key=amount_rank_key)[:k]
        for rank, row in enumerate(ranked, start=1):
            yield {
                "dataset": dataset,
                "date": day,
                "transaction_id": row["transaction_id"],
                "amount": row["amount"],
                "rank": rank,
                "label": row["label"],
            }


def main():
    parser = argparse.ArgumentParser(description="Rank transactions by amount per dataset and day.")
    parser.add_argument("input", type=Path, help="Normalized transaction CSV")
    parser.add_argument("output", type=Path, help="Output alert CSV")
    args = parser.parse_args()

    if args.input.resolve() == args.output.resolve():
        parser.error("input and output must be different files")

    with args.input.open(encoding="utf-8-sig", newline="") as source:
        alerts = list(top_alerts_by_day(csv.DictReader(source)))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, OUTPUT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(alerts)


if __name__ == "__main__":
    main()

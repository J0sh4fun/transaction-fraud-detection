"""Compare daily train and validation activity in Handbook and Sparkov."""

import argparse
from pathlib import Path

import pandas as pd

if __package__:
    from .transaction_features import build_features
else:
    from transaction_features import build_features


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SOURCES = ("handbook", "sparkov")
SPLITS = ("train", "validation")
DAILY_BUDGET = 50
COLUMNS = ["dataset", "timestamp", "entity_id", "amount", "label", "split"]


def summarize_daily(path: Path) -> pd.DataFrame:
    chunks = pd.read_csv(
        path,
        usecols=COLUMNS,
        dtype={"entity_id": "string"},
        chunksize=200_000,
    )
    transactions = pd.concat(
        [chunk.loc[chunk["split"].isin(SPLITS)] for chunk in chunks],
        ignore_index=True,
    )
    # Compute both splits together so validation can use earlier train activity.
    history = build_features(transactions, feature_set="A+B")["missing_history"]
    daily = (
        transactions.assign(date=transactions["timestamp"].str.slice(0, 10), missing_history=history)
        .groupby(["dataset", "split", "date"], as_index=False)
        .agg(transactions=("label", "size"), frauds=("label", "sum"), missing_history=("missing_history", "sum"))
        .sort_values(["dataset", "date"], ignore_index=True)
    )
    daily["reviewed_at_50"] = daily["transactions"].clip(upper=DAILY_BUDGET)
    for count, ratio in (
        ("frauds", "fraud_rate"),
        ("missing_history", "missing_history_rate"),
        ("reviewed_at_50", "review_rate_at_50"),
    ):
        daily[ratio] = daily[count] / daily["transactions"]
    return daily


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Destination CSV for the daily comparison")
    args = parser.parse_args()

    daily = pd.concat(
        [summarize_daily(DATA_DIR / f"{dataset}_183_days.csv.gz") for dataset in SOURCES],
        ignore_index=True,
    )
    daily.to_csv(args.output, index=False, float_format="%.10f", lineterminator="\n")


if __name__ == "__main__":
    main()

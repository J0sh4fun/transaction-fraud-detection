"""Build the 183-day Sparkov table and daily feature quality statistics."""

import argparse
import gzip
from io import TextIOWrapper
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import numpy as np
import pandas as pd

if __package__:
    from .prepare_sparkov_sample import COLUMN_MAP, SOURCE_FILES
    from .transaction_features import build_features
else:
    from prepare_sparkov_sample import COLUMN_MAP, SOURCE_FILES
    from transaction_features import build_features


CALENDAR = Path(__file__).resolve().parents[1] / "data" / "sparkov_183_days.csv"
SPLIT_DAYS = {"train": 90, "validation": 30, "test": 63}


def normalize(source: Path) -> tuple[pd.DataFrame, pd.Series]:
    calendar = pd.read_csv(CALENDAR, dtype={"date": "string"})["date"]
    dates = pd.to_datetime(calendar, format="%Y-%m-%d")
    if (
        len(dates) != sum(SPLIT_DAYS.values())
        or dates.isna().any()
        or not dates.diff().iloc[1:].eq(pd.Timedelta(days=1)).all()
    ):
        raise ValueError("Stage 1 calendar must contain 183 consecutive dates.")

    source_columns = list(COLUMN_MAP)
    chunks = []
    with ZipFile(source) as archive:
        for filename in SOURCE_FILES:
            with archive.open(filename) as stream:
                for raw in pd.read_csv(stream, usecols=source_columns, dtype="string", chunksize=200_000):
                    raw = raw[source_columns].rename(columns=COLUMN_MAP)
                    timestamp = pd.to_datetime(raw["timestamp"], format="%Y-%m-%d %H:%M:%S")
                    if timestamp.isna().any():
                        raise ValueError(f"{filename}: missing timestamp.")
                    selected = timestamp.ge(dates.iloc[0]) & timestamp.lt(dates.iloc[-1] + pd.Timedelta(days=1))
                    if selected.any():
                        chunks.append(raw.loc[selected].assign(timestamp=timestamp.loc[selected]))

    if not chunks:
        raise ValueError("No transactions found in the selected dates.")
    transactions = pd.concat(chunks, ignore_index=True)
    transactions = transactions.sort_values(["timestamp", "transaction_id"], ignore_index=True)
    date_by_transaction = transactions["timestamp"].dt.normalize()
    missing_days = pd.Index(dates).difference(date_by_transaction.unique())
    if not missing_days.empty:
        raise ValueError(f"Missing transaction days: {missing_days.strftime('%Y-%m-%d').tolist()}")

    ids = transactions["transaction_id"]
    if ids.isna().any() or not ids.is_unique:
        raise ValueError("Missing or duplicate Sparkov transaction IDs.")
    if not transactions["entity_id"].str.fullmatch(r"[0-9]+", na=False).all():
        raise ValueError("Missing or invalid Sparkov card IDs.")
    amounts = pd.to_numeric(transactions["amount"], errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
    if not np.isfinite(amounts).all() or (amounts < 0).any():
        raise ValueError("Missing, non-finite or negative Sparkov amounts.")
    if not transactions["label"].isin(["0", "1"]).all():
        raise ValueError("Sparkov labels must be 0 or 1.")
    transactions["label"] = transactions["label"].astype("int8")

    split_by_date = pd.Series(
        [split for split, days in SPLIT_DAYS.items() for _ in range(days)],
        index=dates,
    )
    transactions.insert(0, "dataset", "sparkov")
    transactions["split"] = date_by_transaction.map(split_by_date)
    return transactions, date_by_transaction


def prepare(source: Path, output: Path, daily_output: Path) -> None:
    if len({path.resolve() for path in (source, output, daily_output, CALENDAR)}) != 4:
        raise ValueError("Source, calendar and outputs must be different files.")
    transactions, dates = normalize(source)
    # Compute once across all splits so card history can cross split boundaries.
    features = build_features(transactions, feature_set="A+B")
    daily = (
        pd.DataFrame(
            {
                "date": dates,
                "split": transactions["split"],
                "label": transactions["label"],
                "missing_history": features["missing_history"],
            }
        )
        .groupby(["date", "split"], sort=True, as_index=False)
        .agg(transactions=("label", "size"), frauds=("label", "sum"), missing_history=("missing_history", "sum"))
    )

    for path in (output, daily_output):
        path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as table_dir, TemporaryDirectory(dir=daily_output.parent) as daily_dir:
        temporary_table = Path(table_dir) / output.name
        temporary_daily = Path(daily_dir) / daily_output.name
        with (
            temporary_table.open("wb") as compressed,
            gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as gzipped,
            TextIOWrapper(gzipped, encoding="utf-8", newline="") as csv_file,
        ):
            transactions.to_csv(csv_file, index=False, date_format="%Y-%m-%d %H:%M:%S", lineterminator="\n")
        daily.to_csv(temporary_daily, index=False, date_format="%Y-%m-%d", lineterminator="\n")
        temporary_table.replace(output)
        temporary_daily.replace(daily_output)

    for split, group in daily.groupby("split", sort=False):
        print(f"{split}: {len(group)} days, {group.transactions.sum():,} transactions, {group.frauds.sum():,} frauds")
    print(f"{len(features):,} rows with {len(features.columns)} shared features")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Original Sparkov ZIP downloaded from Kaggle")
    parser.add_argument("output", type=Path, help="Destination normalized CSV.gz")
    parser.add_argument("daily_output", type=Path, help="Destination daily statistics CSV")
    args = parser.parse_args()
    prepare(args.source, args.output, args.daily_output)


if __name__ == "__main__":
    main()

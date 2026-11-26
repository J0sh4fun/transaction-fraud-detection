"""Independently audit Sparkov split boundaries and strictly prior card history."""

import argparse
from bisect import bisect_left
from datetime import timedelta
from hashlib import file_digest
from pathlib import Path
from statistics import median
from zipfile import ZipFile

import numpy as np
import pandas as pd

if __package__:
    from .prepare_sparkov_sample import COLUMN_MAP, SOURCE_FILES
    from .transaction_features import FEATURES_B, build_features
else:
    from prepare_sparkov_sample import COLUMN_MAP, SOURCE_FILES
    from transaction_features import FEATURES_B, build_features


DATA = Path(__file__).resolve().parents[1] / "data"
SOURCE_SHA256 = "4e32829b9ba5a6b17af707c513c15204011044df0e8971e431cedca3d8c0a8a1"
PERIODS = (
    ("train", "2019-01-02", "2019-04-01", 90),
    ("validation", "2019-04-02", "2019-05-01", 30),
    ("test", "2019-05-02", "2019-07-03", 63),
)
HOUR = 3600
DAY = 24 * HOUR


def verify_source(source_path, table, dates):
    with source_path.open("rb") as stream:
        if file_digest(stream, "sha256").hexdigest() != SOURCE_SHA256:
            raise ValueError("Sparkov ZIP SHA-256 differs from the Stage 1 source.")
        stream.seek(0)
        source_rows = []
        with ZipFile(stream) as archive:
            for name in SOURCE_FILES:
                with archive.open(name) as raw:
                    for chunk in pd.read_csv(raw, dtype="string", usecols=list(COLUMN_MAP), chunksize=200_000):
                        chunk = chunk.rename(columns=COLUMN_MAP)
                        source_rows.append(chunk.loc[chunk["timestamp"].str[:10].isin(dates)])

    fields = list(COLUMN_MAP.values())
    raw = pd.concat(source_rows, ignore_index=True)[fields].sort_values("transaction_id", ignore_index=True)
    delivered = table[fields].sort_values("transaction_id", ignore_index=True)
    pd.testing.assert_frame_equal(delivered, raw)


def reference_history(card):
    """Use binary searches and an explicit median on one card's past transactions."""
    times = (card["timestamp"].astype("int64") // 1_000_000_000).tolist()
    amounts = card["amount"].tolist()
    for time, amount in zip(times, amounts):
        end = bisect_left(times, time)
        first_7d = bisect_left(times, time - 7 * DAY, hi=end)
        window = amounts[first_7d:end]
        usual_amount = median(window) if window else 0
        yield (
            end - bisect_left(times, time - HOUR, hi=end),
            end - bisect_left(times, time - DAY, hi=end),
            time - times[end - 1] if end else np.nan,
            amount / usual_amount if usual_amount > 0 else np.nan,
            int(not window),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Original Sparkov ZIP from Stage 1")
    args = parser.parse_args()

    table = pd.read_csv(DATA / "sparkov_183_days.csv.gz", dtype="string")
    if not table["dataset"].eq("sparkov").all() or not table["transaction_id"].is_unique or table.isna().any().any():
        raise ValueError("Unexpected source, missing values, or duplicate transaction IDs.")
    dates = table["timestamp"].str[:10]
    if not dates.is_monotonic_increasing:
        raise ValueError("Sparkov dates are out of order.")
    expected_calendar = []
    for split, start, end, count in PERIODS:
        expected = pd.date_range(start, end).strftime("%Y-%m-%d").tolist()
        if len(expected) != count or dates[table["split"].eq(split)].unique().tolist() != expected:
            raise ValueError(f"Unexpected dates in {split}.")
        expected_calendar.extend(expected)
    if dates.unique().tolist() != expected_calendar or set(table["split"]) != {period[0] for period in PERIODS}:
        raise ValueError("Unexpected dates or split names.")
    verify_source(args.source, table, expected_calendar)
    print(f"{len(table)} transactions match the pinned ZIP and cover the three date ranges.")

    table["timestamp"] = pd.to_datetime(table["timestamp"], format="%Y-%m-%d %H:%M:%S").dt.as_unit("ns")
    table["amount"] = pd.to_numeric(table["amount"])
    table["label"] = pd.to_numeric(table["label"])
    if not table["timestamp"].is_monotonic_increasing or set(table["label"]) != {0, 1}:
        raise ValueError("Timestamps are out of order or the fraud labels are invalid.")
    features = build_features(table)
    for _, transactions in table.groupby("entity_id", sort=False):
        actual = features.loc[transactions.index, list(FEATURES_B)]
        np.testing.assert_allclose(actual, list(reference_history(transactions)), rtol=1e-12, atol=0)
    tied_rows = table.duplicated(["entity_id", "timestamp"], keep=False).sum()
    print(f"All five history features match the independent calculation, including {tied_rows} same-time rows.")

    daily = table.assign(date=dates, missing_history=features["missing_history"]).groupby(
        ["date", "split"], as_index=False,
    ).agg(transactions=("label", "size"), frauds=("label", "sum"), missing_history=("missing_history", "sum"))
    published = pd.read_csv(DATA / "sparkov_daily_stats.csv", dtype={"date": "string", "split": "string"})
    pd.testing.assert_frame_equal(daily, published, check_dtype=False)

    for split, start, _, _ in PERIODS[1:]:
        before = table["timestamp"].lt(start)
        pd.testing.assert_frame_equal(build_features(table.loc[before]), features.loc[before])
        index = dates[dates.eq(start)].index[0]
        target = table.loc[index]
        timestamp = target["timestamp"].to_pydatetime()
        card = table.loc[table["entity_id"].eq(target["entity_id"])]
        prior = card.loc[card["timestamp"].lt(timestamp)]
        previous = prior.iloc[-1]
        expected_previous_split = "train" if split == "validation" else "validation"
        if target["split"] != split or previous["split"] != expected_previous_split:
            raise ValueError(f"Boundary case did not cross into {split} from {expected_previous_split}.")
        additions = table.loc[[index, index]].copy()
        additions["transaction_id"] = ["audit-same-time", "audit-future"]
        additions["timestamp"] = [timestamp, timestamp + timedelta(seconds=1)]
        additions["amount"] = [1_000_000, 2_000_000]
        altered = pd.concat([prior, table.loc[[index]], additions], ignore_index=True)
        pd.testing.assert_series_equal(build_features(altered).iloc[len(prior)], features.loc[index], check_names=False)
        print(f"{split}: {target['transaction_id']} at {target['timestamp']}")
        print(f"previous: {previous['transaction_id']} at {previous['timestamp']} ({previous['split']})")
        recent = prior.loc[prior["timestamp"].ge(timestamp - timedelta(days=7))]
        print(f"7-day history: {len(recent)} rows, median {recent['amount'].median():.6f}, amount {target['amount']}")
        print(features.loc[index, list(FEATURES_B)].to_dict())
    print("Both prefix checks, both same-time/future checks, and all 183 daily statistics passed.")


if __name__ == "__main__":
    main()

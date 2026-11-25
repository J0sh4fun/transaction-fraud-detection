"""Convert one Sparkov day to the shared schema and list the first 183 full days."""

import argparse
import csv
from collections import Counter
from datetime import datetime, time, timedelta
from io import TextIOWrapper
from pathlib import Path
from zipfile import ZipFile


SOURCE_FILES = ("fraudTrain.csv", "fraudTest.csv")
COLUMN_MAP = {
    "trans_num": "transaction_id",
    "trans_date_trans_time": "timestamp",
    "cc_num": "entity_id",
    "amt": "amount",
    "is_fraud": "label",
}
DAY = timedelta(days=1)


def source_rows(archive, filename):
    with archive.open(filename) as raw:
        with TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = COLUMN_MAP.keys() - set(reader.fieldnames or ())
            if missing:
                raise ValueError(f"{filename}: missing columns {sorted(missing)}")
            yield from reader


def prepare(source, sample_output, days_output):
    daily_labels = Counter()
    first = datetime.max
    last = datetime.min
    with ZipFile(source) as archive:
        for filename in SOURCE_FILES:
            for row in source_rows(archive, filename):
                timestamp = datetime.fromisoformat(row["trans_date_trans_time"])
                label = row["is_fraud"]
                if label not in {"0", "1"}:
                    raise ValueError(f"{filename}: invalid label {label!r}")
                daily_labels[timestamp.date(), label] += 1
                first = min(first, timestamp)
                last = max(last, timestamp)

        if not daily_labels:
            raise ValueError("The source ZIP has no transactions")
        # Require the whole midnight-to-midnight interval to fall inside
        # the timestamp range observed across the two source files.
        first_day = first.date()
        if first.time() != time.min:
            first_day += DAY
        days = [first_day + index * DAY for index in range(183)]
        if days[-1] + DAY > last.date():
            raise ValueError("The observed range does not cover 183 full calendar days")
        missing_days = [day for day in days if not (daily_labels[day, "0"] + daily_labels[day, "1"])]
        if missing_days:
            raise ValueError(f"No source transactions on the following selected dates: {missing_days}")

        sample_day = next(
            (day for day in days if daily_labels[day, "0"] and daily_labels[day, "1"]),
            days[0],
        )
        sample_prefix = sample_day.isoformat()
        sample = []
        for filename in SOURCE_FILES:
            for row in source_rows(archive, filename):
                if row["trans_date_trans_time"][:10] == sample_prefix:
                    sample.append(("sparkov", *(row[column] for column in COLUMN_MAP)))

    sample.sort(key=lambda row: (row[2], row[1]))
    labels = Counter(row[-1] for row in sample)
    expected = Counter({label: daily_labels[sample_day, label] for label in ("0", "1")})
    if labels != expected or len({row[1] for row in sample}) != len(sample):
        raise ValueError("Sample labels differ from the source or transaction IDs are duplicated")

    with sample_output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["dataset", *COLUMN_MAP.values()])
        writer.writerows(sample)
    with days_output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["date"])
        writer.writerows([day.isoformat()] for day in days)

    print(f"Source: {sum(daily_labels.values()):,} rows, {first} to {last}")
    print(f"Calendar: {len(days)} consecutive days, {days[0]} to {days[-1]}")
    print(f"Sample {sample_day}: {len(sample):,} rows, label=0: {labels['0']:,}, label=1: {labels['1']:,}")
    print(f"Sample timestamps: {sample[0][2]} to {sample[-1][2]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Original Sparkov ZIP downloaded from Kaggle")
    parser.add_argument("sample_output", type=Path, help="Destination CSV for the sample day")
    parser.add_argument("days_output", type=Path, help="Destination CSV for the 183 dates")
    args = parser.parse_args()
    prepare(args.source, args.sample_output, args.days_output)


if __name__ == "__main__":
    main()

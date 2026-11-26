"""Build the normalized 183-day Handbook table from the pinned source archive."""

import argparse
import gzip
from datetime import date, timedelta
from hashlib import file_digest
from io import TextIOWrapper
from pathlib import Path
from tarfile import open as open_tar
from tempfile import NamedTemporaryFile

import numpy as np
import pandas as pd

if __package__:
    from .prepare_handbook_sample import COLUMN_MAP
else:
    from prepare_handbook_sample import COLUMN_MAP


SOURCE_COMMIT = "6e67dbd0a3bfe0d7ec33abc4bce5f37cd4ff0d6a"
SOURCE_SHA256 = "8b3b161a9d583858db63df4a1ede415b19c28201e3dfb29fc9ac2405b99cc596"
FIRST_DAY = date(2018, 4, 1)
SPLIT_DAYS = {"train": 90, "validation": 30, "test": 63}


def prepare(source: Path, output: Path) -> None:
    if source.resolve() == output.resolve():
        raise ValueError("Source and output must be different files.")

    output.parent.mkdir(parents=True, exist_ok=True)
    summary = {split: [0, 0] for split in SPLIT_DAYS}
    seen_ids = set()
    day = FIRST_DAY

    with source.open("rb") as archive_file:
        # Pickle can execute code. Verify the exact archive before reading any member.
        if file_digest(archive_file, "sha256").hexdigest() != SOURCE_SHA256:
            raise ValueError("Source SHA-256 does not match the pinned Handbook archive.")
        archive_file.seek(0)

        with NamedTemporaryFile(dir=output.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)

        try:
            with (
                open_tar(fileobj=archive_file, mode="r:gz") as archive,
                temporary_path.open("wb") as compressed,
                gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as gzipped,
                TextIOWrapper(gzipped, encoding="utf-8", newline="") as csv_file,
            ):
                for split, days in SPLIT_DAYS.items():
                    for _ in range(days):
                        member_name = f"simulated-data-raw-{SOURCE_COMMIT}/data/{day}.pkl"
                        with archive.extractfile(member_name) as pickle:
                            raw = pd.read_pickle(pickle)
                        transactions = raw[list(COLUMN_MAP)].rename(columns=COLUMN_MAP)
                        timestamps = transactions["timestamp"]
                        if transactions.empty or not timestamps.dt.date.eq(day).all():
                            raise ValueError(f"{day}: missing transactions or timestamp outside the day.")
                        ids = transactions["transaction_id"]
                        if ids.isna().any() or not ids.is_unique or not seen_ids.isdisjoint(ids):
                            raise ValueError(f"{day}: missing or duplicate transaction IDs.")
                        seen_ids.update(ids)
                        amounts = transactions["amount"]
                        if (
                            transactions["entity_id"].isna().any()
                            or not np.isfinite(amounts).all()
                            or (amounts < 0).any()
                            or not transactions["label"].isin([0, 1]).all()
                        ):
                            raise ValueError(f"{day}: invalid entity, amount or label.")

                        transactions.insert(0, "dataset", "handbook")
                        transactions["split"] = split
                        transactions.sort_values(["timestamp", "transaction_id"]).to_csv(
                            csv_file,
                            index=False,
                            header=day == FIRST_DAY,
                            date_format="%Y-%m-%d %H:%M:%S",
                            float_format="%.2f",
                            lineterminator="\n",
                        )
                        summary[split][0] += len(transactions)
                        summary[split][1] += int(transactions["label"].sum())
                        day += timedelta(days=1)
            temporary_path.replace(output)
        finally:
            temporary_path.unlink(missing_ok=True)

    for split, (transactions, frauds) in summary.items():
        print(f"{split}: {SPLIT_DAYS[split]} days, {transactions:,} transactions, {frauds:,} frauds")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Pinned Handbook tar.gz archive")
    parser.add_argument("output", type=Path, help="Destination CSV.gz")
    args = parser.parse_args()
    prepare(args.source, args.output)


if __name__ == "__main__":
    main()

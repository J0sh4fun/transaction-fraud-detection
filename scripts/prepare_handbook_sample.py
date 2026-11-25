"""Convert the pinned Handbook day to the shared transaction schema."""

import argparse
from hashlib import sha256
from pathlib import Path

import pandas as pd


SOURCE_SHA256 = "6bb3398e858be68532e22522ed8dd52601fe507b6537f6bc2dde0abcdd3e4717"
SAMPLE_DATE = "2018-04-01"
COLUMN_MAP = {
    "TRANSACTION_ID": "transaction_id",
    "TX_DATETIME": "timestamp",
    "CUSTOMER_ID": "entity_id",
    "TX_AMOUNT": "amount",
    "TX_FRAUD": "label",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Official 2018-04-01.pkl file")
    parser.add_argument("output", type=Path, help="Destination CSV")
    args = parser.parse_args()

    # Pickle can execute code. Only deserialize the pinned source file.
    with args.source.open("rb") as source:
        if sha256(source.read()).hexdigest() != SOURCE_SHA256:
            parser.error("Source SHA-256 does not match the pinned Handbook file.")
        source.seek(0)
        raw = pd.read_pickle(source)

    transactions = raw[list(COLUMN_MAP)].rename(columns=COLUMN_MAP)
    transactions.insert(0, "dataset", "handbook")
    transactions.to_csv(
        args.output,
        index=False,
        date_format="%Y-%m-%d %H:%M:%S",
        float_format="%.2f",
        lineterminator="\n",
    )
    print(
        f"{SAMPLE_DATE}: {len(transactions)} transactions, "
        f"{transactions['label'].sum()} frauds, "
        f"{transactions['timestamp'].min()} to {transactions['timestamp'].max()}"
    )


if __name__ == "__main__":
    main()

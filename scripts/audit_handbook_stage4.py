"""Audit Handbook source labels, transaction keys and actual model input columns."""

import argparse
import sys
from collections import Counter
from datetime import timedelta
from hashlib import file_digest
from pathlib import Path
from tarfile import open as open_tar

import numpy as np
import pandas as pd

if __package__:
    from .prepare_handbook_stage2 import SOURCE_COMMIT, SOURCE_SHA256, FIRST_DAY, SPLIT_DAYS
    from .prepare_handbook_sample import COLUMN_MAP
    from .transaction_features import FEATURES_A, FEATURES_B, build_features
else:
    from prepare_handbook_stage2 import SOURCE_COMMIT, SOURCE_SHA256, FIRST_DAY, SPLIT_DAYS
    from prepare_handbook_sample import COLUMN_MAP
    from transaction_features import FEATURES_A, FEATURES_B, build_features

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ml.preprocessing import (  # noqa: E402
    ALGORITHMS, build_model_pipeline, get_feature_columns, select_feature_frame,
    validate_feature_columns,
)


def audit(source):
    table = pd.read_csv(ROOT / "data/handbook_183_days.csv.gz",
                        dtype={"transaction_id": "string", "entity_id": "string"})
    expected_schema = ["dataset", *COLUMN_MAP.values(), "split"]
    if list(table.columns) != expected_schema or not table.dataset.eq("handbook").all():
        raise ValueError("Unexpected normalized schema or dataset.")
    if table.isna().any().any() or not table.transaction_id.is_unique:
        raise ValueError("Missing values or duplicate transaction keys.")
    if not table.label.isin([0, 1]).all():
        raise ValueError("Invalid binary labels.")
    table["timestamp"] = pd.to_datetime(table.timestamp)
    if not table.timestamp.is_monotonic_increasing:
        raise ValueError("Table is not chronological.")
    by_date = table.groupby(table.timestamp.dt.date)
    scenarios = Counter()
    rows = 0
    day = FIRST_DAY
    with source.open("rb") as stream:
        if file_digest(stream, "sha256").hexdigest() != SOURCE_SHA256:
            raise ValueError("Source archive does not match the pinned SHA-256.")
        stream.seek(0)
        # Only read pickle members after verifying the pinned archive.
        with open_tar(fileobj=stream, mode="r:gz") as archive:
            for split, days in SPLIT_DAYS.items():
                for _ in range(days):
                    member = f"simulated-data-raw-{SOURCE_COMMIT}/data/{day}.pkl"
                    with archive.extractfile(member) as raw_stream:
                        raw = pd.read_pickle(raw_stream)
                    if raw.TX_FRAUD_SCENARIO.isna().any():
                        raise ValueError(f"{day}: missing scenario.")
                    if not raw.TX_FRAUD_SCENARIO.isin([0, 1, 2, 3]).all():
                        raise ValueError(f"{day}: unexpected scenario codes.")
                    np.testing.assert_array_equal(raw.TX_FRAUD, raw.TX_FRAUD_SCENARIO.ne(0).astype(int))
                    scenarios.update(zip(raw.TX_FRAUD_SCENARIO.astype(int), raw.TX_FRAUD.astype(int)))
                    expected = raw[list(COLUMN_MAP)].rename(columns=COLUMN_MAP)
                    expected["transaction_id"] = expected.transaction_id.astype("string")
                    expected["entity_id"] = expected.entity_id.astype("string")
                    delivered = by_date.get_group(day)
                    assert delivered.split.eq(split).all()
                    expected = expected.sort_values("transaction_id").reset_index(drop=True)
                    actual = delivered[list(COLUMN_MAP.values())].sort_values("transaction_id").reset_index(drop=True)
                    # The normalized source contract writes currency to two decimal places.
                    expected["amount"] = expected.amount.map(lambda value: f"{value:.2f}")
                    actual["amount"] = actual.amount.map(lambda value: f"{value:.2f}")
                    pd.testing.assert_frame_equal(actual, expected, check_dtype=False, check_exact=True)
                    rows += len(raw)
                    day += timedelta(days=1)
    assert rows == len(table) and len(by_date) == sum(SPLIT_DAYS.values())
    print(f"Source comparison passed: {rows:,} unique transactions, {int(table.label.sum()):,} frauds, 183 days.")
    print(f"(scenario, label) counts: {dict(sorted(scenarios.items()))}")

    # Use the same feature builder and entry points as run_stage3_validation.py.
    observed = table.loc[table.split.isin(["train", "validation"])].copy()
    features = build_features(observed)
    assert tuple(features.columns) == FEATURES_A + FEATURES_B
    poisoned = observed.copy()
    poisoned["label"] = 1 - poisoned.label
    poisoned["TX_FRAUD_SCENARIO"] = 999
    pd.testing.assert_frame_equal(build_features(poisoned), features, check_exact=True)
    train = observed.split.eq("train")
    validation = observed.split.eq("validation")
    for feature_set, expected in (("A", FEATURES_A), ("A+B", FEATURES_A + FEATURES_B)):
        assert get_feature_columns(feature_set) == list(expected)
        candidates = features.assign(label=observed.label, TX_FRAUD_SCENARIO=999,
                                     transaction_id=observed.transaction_id)
        selected = select_feature_frame(candidates, feature_set)
        assert list(selected.columns) == list(expected)
        for algorithm in ALGORITHMS:
            pipeline = build_model_pipeline(algorithm, feature_set)
            preprocessor = pipeline.named_steps["preprocess"]
            preprocessor.fit(selected.loc[train])
            used = [column for _, _, columns in preprocessor.transformers
                    for column in columns]
            assert set(used) == set(expected) and len(used) == len(expected)
            transformed = preprocessor.transform(selected.loc[validation])
            assert transformed.shape == (int(validation.sum()), len(expected))
            print(f"{algorithm} {feature_set}: {used}; validation shape {transformed.shape}")
    for forbidden in ("label", "TX_FRAUD", "TX_FRAUD_SCENARIO", "transaction_id", "entity_id"):
        try:
            validate_feature_columns([*FEATURES_A, forbidden])
        except ValueError:
            continue
        raise AssertionError(f"Forbidden model column accepted: {forbidden}")
    print("Labels/scenarios leave features unchanged; forbidden inputs rejected.")
    print("All Handbook Stage 4 checks passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Pinned Handbook tar.gz archive")
    audit(parser.parse_args().source)

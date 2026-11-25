"""Check the shared features against hand-calculated results for task 2.1."""

import numpy as np
import pandas as pd

if __package__:
    from .transaction_features import FEATURES_A, FEATURES_B, build_features
else:
    from transaction_features import FEATURES_A, FEATURES_B, build_features


def main() -> None:
    columns = ["transaction_id", "dataset", "entity_id", "timestamp", "amount", "split"]
    transactions = pd.DataFrame(
        [
            ("seven_days", "handbook", "01", "2018-06-23 00:00:00", 10, "train"),
            ("one_day", "handbook", "01", "2018-06-29 00:00:00", 20, "train"),
            ("one_hour", "handbook", "01", "2018-06-29 23:00:00", 30, "train"),
            ("tie_1", "handbook", "01", "2018-06-29 23:30:00", 40, "train"),
            ("tie_2", "handbook", "01", "2018-06-29 23:30:00", 60, "train"),
            ("validation_first", "handbook", "01", "2018-06-30 00:00:00", 90, "validation"),
            ("new_entity", "handbook", "02", "2018-06-30 00:00:00", 80, "validation"),
            ("sparkov_history", "sparkov", "01", "2018-06-29 23:45:00", 5, "train"),
            ("sparkov_same_id", "sparkov", "01", "2018-06-30 00:00:00", 20, "validation"),
            ("test_first", "handbook", "01", "2018-07-30 00:00:00", 100, "test"),
        ],
        columns=columns,
    ).set_index("transaction_id")
    transactions = transactions.sample(frac=1, random_state=42)
    combined = build_features(transactions)
    pd.testing.assert_index_equal(combined.index, transactions.index)
    assert tuple(combined.columns) == FEATURES_A + FEATURES_B
    basic = build_features(transactions, "A")
    pd.testing.assert_frame_equal(basic, combined[list(FEATURES_A)])
    saturday_angle = 2 * np.pi * 5 / 7
    np.testing.assert_allclose(
        basic.loc["validation_first"],
        [np.log(91), 0, 1, np.sin(saturday_angle), np.cos(saturday_angle)],
    )

    expected = pd.DataFrame.from_dict(
        {
            "tie_1": (1, 2, 1800, 2, 0),
            "tie_2": (1, 2, 1800, 3, 0),
            "validation_first": (3, 4, 1800, 3, 0),
            "new_entity": (0, 0, np.nan, np.nan, 1),
            "sparkov_same_id": (1, 1, 900, 4, 0),
            "test_first": (0, 0, 30 * 86400, np.nan, 1),
        },
        orient="index",
        columns=list(FEATURES_B),
    ).rename_axis("transaction_id")
    actual = combined.loc[expected.index, list(FEATURES_B)]
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False)

    future = transactions.loc[["validation_first"]].rename(index={"validation_first": "future"})
    future["timestamp"] = "2018-07-31 00:00:00"
    future["amount"] = 1_000_000
    future["split"] = "test"
    with_future = build_features(pd.concat([future, transactions]))
    pd.testing.assert_frame_equal(with_future.loc[transactions.index], combined)

    print(actual.to_string())
    print("A matches A+B, and adding a future transaction leaves all earlier features unchanged.")


if __name__ == "__main__":
    main()

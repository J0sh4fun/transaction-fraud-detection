"""Build A or A+B features for normalized Handbook and Sparkov transactions."""

import numpy as np
import pandas as pd
from pandas.api.indexers import BaseIndexer


FEATURES_A = ("log_amount", "hour_sin", "hour_cos", "dow_sin", "dow_cos")
FEATURES_B = (
    "count_1h",
    "count_24h",
    "seconds_since_previous",
    "amount_to_median_7d",
    "missing_history",
)


class HistoryWindow(BaseIndexer):
    def __init__(self, start, end):
        super().__init__()
        self.start = start
        self.end = end

    def get_window_bounds(self, num_values, min_periods, center, closed, step):
        return self.start, self.end


def build_features(transactions: pd.DataFrame, feature_set: str = "A+B") -> pd.DataFrame:
    """Return only feature columns, in the same row order and index as the input.

    Pass the chronological coverage of all splits together for A+B so the first
    rows of validation and test can use activity from earlier splits.
    """
    if feature_set not in ("A", "A+B"):
        raise ValueError("feature_set must be 'A' or 'A+B'.")

    timestamp = pd.to_datetime(transactions["timestamp"], format="ISO8601")
    amounts = pd.to_numeric(transactions["amount"]).to_numpy(dtype=np.float64, na_value=np.nan)
    if timestamp.isna().any() or not np.isfinite(amounts).all() or (amounts < 0).any():
        raise ValueError("Features require valid timestamps and finite, non-negative amounts.")

    hour = timestamp.dt.hour + timestamp.dt.minute / 60.0
    day_of_week = timestamp.dt.dayofweek
    hour_angle = 2.0 * np.pi * hour / 24.0
    day_angle = 2.0 * np.pi * day_of_week / 7.0
    features = pd.DataFrame(
        {
            "log_amount": np.log1p(amounts),
            "hour_sin": np.sin(hour_angle),
            "hour_cos": np.cos(hour_angle),
            "dow_sin": np.sin(day_angle),
            "dow_cos": np.cos(day_angle),
        },
        index=transactions.index,
    )
    if feature_set == "A":
        return features

    keys = ["dataset", "entity_id"]
    ordered = transactions[keys].reset_index(drop=True)
    if ordered.isna().any().any():
        raise ValueError("History requires a dataset and entity_id for every transaction.")
    ordered = ordered.assign(timestamp=timestamp.array).sort_values([*keys, "timestamp"])
    positions = ordered.index.to_numpy()
    timestamps = ordered["timestamp"].dt.as_unit("ns").astype("int64").to_numpy()
    ordered_amounts = amounts[positions]

    size = len(ordered)
    count_1h = np.empty(size, dtype=np.int64)
    count_24h = np.empty(size, dtype=np.int64)
    previous_gap = np.full(size, np.nan)
    median_start = np.empty(size, dtype=np.int64)
    history_end = np.empty(size, dtype=np.int64)
    hour_ns = pd.Timedelta(hours=1).value
    day_ns = pd.Timedelta(days=1).value
    offset = 0
    for group_size in ordered.groupby(keys, sort=False, observed=True).size():
        group = slice(offset, offset + group_size)
        times = timestamps[group]
        # The first position at t excludes the entire batch at t from history.
        prior = np.searchsorted(times, times, side="left")
        count_1h[group] = prior - np.searchsorted(times, times - hour_ns, side="left")
        count_24h[group] = prior - np.searchsorted(times, times - day_ns, side="left")
        median_start[group] = offset + np.searchsorted(times, times - 7 * day_ns, side="left")
        history_end[group] = offset + prior
        has_previous = prior > 0
        previous_gap[offset + np.flatnonzero(has_previous)] = (
            times[has_previous] - times[prior[has_previous] - 1]
        ) / 1_000_000_000
        offset += group_size

    window = HistoryWindow(median_start, history_end)
    median = pd.Series(ordered_amounts).rolling(window, min_periods=1).median().to_numpy()
    ratio = np.divide(
        ordered_amounts,
        median,
        out=np.full(size, np.nan),
        where=median > 0,
    )
    input_order = positions.argsort()
    features["count_1h"] = count_1h[input_order]
    features["count_24h"] = count_24h[input_order]
    features["seconds_since_previous"] = previous_gap[input_order]
    features["amount_to_median_7d"] = ratio[input_order]
    features["missing_history"] = (median_start == history_end)[input_order].astype(np.int8)
    return features

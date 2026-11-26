"""Analyze locked test scores at K=50 for TV2 task 5.2."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

if __package__:
    from .transaction_features import build_features
else:
    from transaction_features import build_features


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def rank_scores(scores):
    ordered = scores.assign(
        tie_key=pd.to_numeric(scores.transaction_id) if scores.dataset.iloc[0] == "handbook"
        else scores.transaction_id,
    ).sort_values(["date", "risk_score", "tie_key"], ascending=[True, False, True])
    return ordered.assign(rank=ordered.groupby("date").cumcount() + 1).drop(columns="tie_key")


def analyze(output_dir):
    runs = pd.read_csv(DATA / "stage5_test_runs.csv")
    locked = pd.read_csv(DATA / "selected_configurations_stage3.csv")
    keys = ["dataset", "algorithm", "feature_set", "config"]
    assert len(runs) == 12 and not runs.duplicated(keys).any()
    assert set(map(tuple, runs[keys].values)) == set(map(tuple, locked[keys].values))
    daily_tables = []
    cases_scores = {}
    for dataset in ("handbook", "sparkov"):
        source = pd.read_csv(DATA / f"{dataset}_183_days.csv.gz",
                             dtype={"transaction_id": "string", "entity_id": "string"})
        test = source.loc[source.split.eq("test")].copy()
        test["date"] = test.timestamp.str[:10]
        assert test.date.nunique() == 63 and test.transaction_id.is_unique
        first_day = pd.Timestamp(test.date.min())
        for run in runs.loc[runs.dataset.eq(dataset)].itertuples(index=False):
            scores = pd.read_csv(ROOT / run.score_file, dtype={"transaction_id": "string"})
            fields = ["dataset", "transaction_id", "timestamp", "label", "date"]
            pd.testing.assert_frame_equal(scores[fields].reset_index(drop=True),
                                          test[fields].reset_index(drop=True), check_dtype=False)
            assert np.isfinite(scores.risk_score).all()
            assert scores.transaction_id.is_unique
            assert scores.algorithm.eq(run.algorithm).all()
            assert scores.feature_set.eq(run.feature_set).all() and scores.config.eq(run.config).all()
            ranked = rank_scores(scores)
            daily = ranked.assign(found=ranked.label * ranked["rank"].le(50)).groupby("date").agg(
                transactions=("label", "size"), frauds=("label", "sum"), true_positives=("found", "sum"),
            ).reset_index()
            daily["alerts"] = daily.transactions.clip(upper=50)
            daily["week"] = ((pd.to_datetime(daily.date) - first_day).dt.days // 7 + 1)
            daily["dataset"] = dataset
            daily["algorithm"] = run.algorithm
            daily["feature_set"] = run.feature_set
            daily["config"] = run.config
            daily_tables.append(daily)
            if dataset == "sparkov" and run.algorithm == "hist_gradient_boosting":
                cases_scores[run.feature_set] = ranked

    daily = pd.concat(daily_tables, ignore_index=True)
    weekly = daily.groupby(["dataset", "algorithm", "feature_set", "week"]).agg(
        days=("date", "nunique"), start=("date", "min"), end=("date", "max"),
        transactions=("transactions", "sum"), frauds=("frauds", "sum"),
        true_positives=("true_positives", "sum"),
    ).reset_index()
    keys = ["dataset", "algorithm", "week", "days", "start", "end", "transactions", "frauds"]
    weekly = weekly.loc[weekly.feature_set.eq("A")].drop(columns="feature_set").merge(
        weekly.loc[weekly.feature_set.eq("A+B")].drop(columns="feature_set"),
        on=keys, suffixes=("_a", "_ab"), validate="one_to_one",
    )
    assert len(weekly) == 54 and weekly.days.eq(7).all()
    weekly["delta_per_day"] = (weekly.true_positives_ab - weekly.true_positives_a) / weekly.days
    totals = weekly.groupby(["dataset", "algorithm"]).agg(
        days=("days", "sum"), transactions=("transactions", "sum"), frauds=("frauds", "sum"),
        true_positives_a=("true_positives_a", "sum"), true_positives_ab=("true_positives_ab", "sum"),
    ).reset_index()
    totals["delta_per_day"] = (totals.true_positives_ab - totals.true_positives_a) / totals.days
    totals["transactions_per_day"] = totals.transactions / totals.days
    totals["frauds_per_day"] = totals.frauds / totals.days

    # Pick the earliest transaction by date and rank for each case in locked HGB A+B.
    ranked = cases_scores["A+B"]
    rows = []
    for name, mask in (
        ("true_positive", ranked.label.eq(1) & ranked["rank"].le(50)),
        ("false_positive", ranked.label.eq(0) & ranked["rank"].le(50)),
        ("false_negative", ranked.label.eq(1) & ranked["rank"].gt(50)),
    ):
        case = ranked.loc[mask].iloc[0].copy()
        case["case"] = name
        rows.append(case)
    cases = pd.DataFrame(rows)
    basic = cases_scores["A"].set_index("transaction_id")
    cases["rank_a"] = cases.transaction_id.map(basic["rank"])
    cases["risk_score_a"] = cases.transaction_id.map(basic.risk_score)
    source = pd.read_csv(DATA / "sparkov_183_days.csv.gz",
                         dtype={"transaction_id": "string", "entity_id": "string"})
    features = build_features(source)
    feature_rows = pd.concat([source[["transaction_id", "entity_id", "amount"]], features], axis=1)
    cases = cases.merge(feature_rows, on="transaction_id", validate="one_to_one")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in (("daily", daily), ("weekly", weekly), ("comparison", totals), ("cases", cases)):
        table.to_csv(output_dir / f"sparkov_stage5_{name}.csv", index=False, lineterminator="\n")
    print(totals.to_string(index=False))
    print(cases[["case", "transaction_id", "date", "rank", "rank_a", "label", "amount",
                 "count_24h", "amount_to_median_7d"]].to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path, help="Destination directory for analysis CSVs")
    analyze(parser.parse_args().output_dir)

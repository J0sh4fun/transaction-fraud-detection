"""Generate the Handbook test analysis for task 5.1 from locked scores."""

import argparse
from pathlib import Path

import pandas as pd

if __package__:
    from .analyze_handbook_stage3 import markdown_table
    from .analyze_sparkov_stage5 import DATA, ROOT, rank_scores
    from .transaction_features import build_features
else:
    from analyze_handbook_stage3 import markdown_table
    from analyze_sparkov_stage5 import DATA, ROOT, rank_scores
    from transaction_features import build_features


ALGORITHMS = {
    "hist_gradient_boosting": "HistGradientBoosting",
    "isolation_forest": "Isolation Forest",
    "logistic_regression": "Logistic Regression",
}
HGB = "hist_gradient_boosting"
K = 50


def case_rows():
    runs = pd.read_csv(DATA / "stage5_test_runs.csv")
    runs = runs.loc[runs.dataset.eq("handbook") & runs.algorithm.eq(HGB)].set_index("feature_set")
    ranked = {}
    for feature_set in ("A", "A+B"):
        scores = pd.read_csv(ROOT / runs.loc[feature_set, "score_file"], dtype={"transaction_id": "string"})
        ranked[feature_set] = rank_scores(scores).set_index("transaction_id")
    combined = ranked["A+B"].assign(
        rank_a=ranked["A"]["rank"], score_a=ranked["A"]["risk_score"],
    )
    in_a = combined.rank_a.le(K)
    in_ab = combined["rank"].le(K)
    fraud = combined.label.eq(1)
    picked = pd.concat([
        combined.loc[fraud & ~in_a & in_ab].head(1).assign(case="Bắt đúng thêm"),
        combined.loc[~fraud & ~in_a & in_ab].head(1).assign(case="Báo nhầm thêm"),
        combined.loc[fraud & in_a & ~in_ab].head(1).assign(case="Gian lận bị bỏ sót"),
    ])
    if len(picked) != 3:
        raise ValueError("The locked scores do not contain all three cases.")

    ids = {"transaction_id": "string", "entity_id": "string"}
    source = pd.read_csv(DATA / "handbook_183_days.csv.gz", dtype=ids).set_index("transaction_id")
    selected = source.loc[picked.index]
    pd.testing.assert_frame_equal(picked[["timestamp", "label"]], selected[["timestamp", "label"]])
    customer_rows = source.loc[source.entity_id.isin(selected.entity_id)]
    features = build_features(customer_rows)
    return picked.join(selected[["amount", "entity_id"]]).join(features.loc[picked.index]).reset_index()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Destination Markdown report")
    args = parser.parse_args()
    weekly = pd.read_csv(DATA / "sparkov_stage5_weekly.csv").query("dataset == 'handbook'")
    indexed = weekly.set_index(["week", "algorithm"])
    if len(indexed) != 27 or not indexed.index.is_unique or not weekly.days.eq(7).all():
        raise ValueError("Expected nine seven-day weeks for each Handbook algorithm.")
    rows = []
    for week, group in weekly.groupby("week", sort=True):
        first = group.iloc[0]
        cells = []
        for algorithm in ALGORITHMS:
            cell = indexed.loc[(week, algorithm)]
            cells.append(f"{cell.true_positives_a} / {cell.true_positives_ab} ({cell.delta_per_day:+.6f})")
        rows.append((week, f"{first.start} → {first.end}", first.frauds, *cells))
    totals = []
    for algorithm, title in ALGORITHMS.items():
        subset = weekly.loc[weekly.algorithm.eq(algorithm)]
        a, ab = subset[["true_positives_a", "true_positives_ab"]].sum()
        days = subset.days.sum()
        totals.append((title, a, ab, f"{a / days:.6f}", f"{ab / days:.6f}", f"{(ab - a) / days:+.6f}"))

    examples = case_rows()
    lines = [
        "# Phân tích kết quả Handbook · Chặng 5, mục 5.1",
        "",
        "Phân tích sáu cấu hình đã khóa trên 63 ngày test Handbook, từ 30/07 đến 30/09/2018, "
        "gồm 603.785 giao dịch và 5.388 ca gian lận. Mỗi ngày lấy 50 điểm cao nhất và dùng mã giao dịch "
        "theo thứ tự số tăng dần khi bằng điểm. [Nguồn bảng điểm](ml-stage-5.md) · [Quy trình đánh giá](evaluation-stage-4.md)",
        "",
        "## Chênh lệch theo chín tuần",
        "",
        "Mỗi ô mô hình ghi số ca đúng của A / A+B và chênh lệch ca/ngày trong ngoặc. "
        "Chênh lệch bằng (ca đúng A+B − ca đúng A) chia số ngày. "
        "[Bảng theo ngày](../data/sparkov_stage5_daily.csv) · [Bảng tuần hai nguồn, lọc Handbook](../data/sparkov_stage5_weekly.csv)",
        "",
        *markdown_table(("Tuần", "Khoảng ngày", "Gian lận thực tế", *ALGORITHMS.values()), rows),
        "",
        *markdown_table(("Thuật toán", "Ca đúng A", "Ca đúng A+B", "Ca/ngày A", "Ca/ngày A+B", "Chênh lệch ca/ngày"), totals),
        "",
        "HistGradientBoosting A+B dẫn đầu trong sáu cấu hình Handbook, với 1.515 ca đúng. "
        "Cả ba thuật toán tìm được nhiều ca hơn với A+B trên 63 ngày. Logistic Regression dùng C khác nhau "
        "giữa hai bộ đặc trưng, nên chênh lệch phản ánh cả đặc trưng và cấu hình đã chọn.",
        "",
        "## Ba ca điển hình",
        "",
        "Dùng HistGradientBoosting với cùng cấu hình 15 nút lá. Chọn giao dịch đầu tiên theo ngày rồi theo hạng "
        "A+B cho từng nhóm. Ca bắt đúng và báo nhầm mới vào top 50 khi dùng A+B. Ca bỏ sót rời top 50 khi chuyển từ A sang A+B.",
        "",
        *markdown_table(
            ("Ca", "Mã giao dịch", "Thời điểm", "Nhãn", "Hạng A", "Hạng A+B", "Điểm A", "Điểm A+B"),
            (
                (row.case, f"`{row.transaction_id}`", row.timestamp, row.label, row.rank_a, row.rank,
                 f"{row.score_a:.6f}", f"{row.risk_score:.6f}")
                for row in examples.itertuples(index=False)
            ),
        ),
        "",
        *markdown_table(
            ("Mã giao dịch", "Khách hàng", "Số tiền", "GD 1 giờ", "GD 24 giờ", "Giây từ GD trước", "Số tiền / trung vị 7 ngày", "Thiếu lịch sử"),
            (
                (f"`{row.transaction_id}`", f"`{row.entity_id}`", f"{row.amount:.2f}", row.count_1h, row.count_24h,
                 f"{row.seconds_since_previous:.0f}", f"{row.amount_to_median_7d:.6f}", row.missing_history)
                for row in examples.itertuples(index=False)
            ),
        ),
        "",
        "Ba ca minh họa thay đổi thứ hạng quan sát được. Đặc trưng lịch sử được tính trên giao dịch trước thời điểm đang xét của cùng khách hàng. "
        "Dùng mã giao dịch để tra bảng Handbook chuẩn hóa hoặc cột `TRANSACTION_ID` trong tệp nguồn theo ngày. "
        "[Dữ liệu chuẩn hóa](../data/handbook_183_days.csv.gz) · [Từ điển đặc trưng](handbook-stage-2.md#từ-điển-đặc-trưng)",
        "",
        "## Chạy lại",
        "",
        "Chạy từ thư mục gốc repo sau khi cài thư viện trong `requirements.txt`.",
        "",
        "```powershell",
        "$handbookCheck = Join-Path $env:TEMP 'handbook-stage5-check.md'",
        "python scripts/analyze_handbook_stage5.py $handbookCheck",
        "```",
        "",
    ]
    args.output.write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()

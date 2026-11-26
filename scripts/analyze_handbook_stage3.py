"""Report Handbook feature distributions and reviewable train/validation histories."""

import argparse
from datetime import timedelta
from math import isclose
from pathlib import Path

import pandas as pd

if __package__:
    from .transaction_features import build_features
else:
    from transaction_features import build_features


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "handbook_183_days.csv.gz"
SPLITS = ("train", "validation")
EXAMPLES = (
    ("Lịch sử ngắn", "863216"),
    ("Lịch sử dài", "863677"),
    ("Số tiền bất thường", "863087"),
)


def markdown_table(headers, rows):
    def line(values):
        return "| " + " | ".join(map(str, values)) + " |"

    return [line(headers), line(["---"] * len(headers)), *(line(row) for row in rows)]


def distribution_rows(transactions, features):
    for split in SPLITS:
        values = features.loc[transactions["split"].eq(split)]
        quantiles = values.quantile([0.05, 0.5, 0.95])
        for name, missing in values.isna().sum().items():
            yield (
                split,
                f"`{name}`",
                *(f"{value:.6f}" for value in quantiles[name]),
                f"{missing} ({missing / len(values):.4%})",
            )


def example_sections(transactions, features):
    summary = []
    details = []
    for title, transaction_id in EXAMPLES:
        index = transactions.index[transactions["transaction_id"].eq(transaction_id)].item()
        target = transactions.loc[index]
        timestamp = target["timestamp"].to_pydatetime()
        same_customer = transactions["entity_id"].eq(target["entity_id"])
        history = transactions.loc[
            same_customer
            & transactions["timestamp"].ge(timestamp - timedelta(days=7))
            & transactions["timestamp"].lt(timestamp)
        ].sort_values(["timestamp", "transaction_id"])
        in_24h = history["timestamp"].ge(timestamp - timedelta(days=1))
        count = int(in_24h.sum())
        median = history["amount"].median()
        ratio = target["amount"] / median
        computed = features.loc[index]
        if count != computed["count_24h"] or not isclose(ratio, computed["amount_to_median_7d"]):
            raise ValueError(f"Direct history calculation differs for {transaction_id}.")

        summary.append((
            title, f"`{transaction_id}`", f"`{target['entity_id']}`", timestamp,
            f"{target['amount']:.2f}", len(history), count, f"{median:.3f}", f"{ratio:.6f}",
        ))
        rows = (
            (f"`{row.transaction_id}`", row.timestamp, f"{row.amount:.2f}", row.split, "Có" if included else "—")
            for row, included in zip(history.itertuples(index=False), in_24h)
        )
        details.extend([
            f"### {title} · `{transaction_id}`",
            "",
            *markdown_table(("Mã giao dịch", "Thời điểm", "Số tiền", "Tập", "Trong 24 giờ"), rows),
            "",
        ])
    return summary, details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Destination Markdown report")
    args = parser.parse_args()

    chunks = pd.read_csv(
        DATA_PATH,
        usecols=["dataset", "transaction_id", "timestamp", "entity_id", "amount", "split"],
        dtype={"transaction_id": "string", "entity_id": "string"},
        chunksize=200_000,
    )
    transactions = pd.concat(
        [chunk.loc[chunk["split"].isin(SPLITS)] for chunk in chunks],
        ignore_index=True,
    )
    transactions["timestamp"] = pd.to_datetime(transactions["timestamp"], format="%Y-%m-%d %H:%M:%S")
    features = build_features(transactions, feature_set="A+B")
    split_sizes = transactions["split"].value_counts()
    train_size = f"{split_sizes['train']:,}".replace(",", ".")
    validation_size = f"{split_sizes['validation']:,}".replace(",", ".")
    missing_history = features["missing_history"].groupby(transactions["split"]).mean()
    examples, histories = example_sections(transactions, features)
    lines = [
        "# Đặc trưng lịch sử Handbook · Chặng 3, mục 3.1",
        "",
        "Dữ liệu lấy từ [bảng Handbook đã chia tập](../data/handbook_183_days.csv.gz). "
        "Tính A+B trên train và validation cùng lúc để giữ lịch sử qua ranh giới hai tập. "
        "[Từ điển đặc trưng và nguồn gốc dữ liệu](handbook-stage-2.md#từ-điển-đặc-trưng)",
        "",
        "## Phân bố đặc trưng",
        "",
        f"Train có {train_size} giao dịch và validation có {validation_size} giao dịch. "
        "P05, P50 và P95 tính trên các giá trị có mặt. Cột thiếu dùng tổng số dòng của tập làm mẫu số.",
        "",
        *markdown_table(
            ("Tập", "Đặc trưng", "P05", "P50", "P95", "Số dòng thiếu (%)"),
            distribution_rows(transactions, features),
        ),
        "",
        f"Tỷ lệ giao dịch có `missing_history = 1` là {missing_history['train']:.4%} trên train "
        f"và {missing_history['validation']:.4%} trên validation.",
        "",
        "## Đối chiếu ba giao dịch",
        "",
        "Ba giao dịch được chọn trong ngày đầu validation để thấy cách đặc trưng dùng lịch sử train. "
        "Bảng dưới ghi kết quả tính trực tiếp từ số tiền và thời điểm của cùng khách hàng. "
        "Cả số giao dịch 24 giờ và tỷ lệ số tiền đều khớp với hàm A+B.",
        "",
        *markdown_table(
            ("Ca", "Mã giao dịch", "Khách hàng", "Thời điểm", "Số tiền",
             "Số GD 7 ngày", "Số GD 24 giờ", "Trung vị 7 ngày", "Số tiền / trung vị"),
            examples,
        ),
        "",
        "Đếm các dòng đánh dấu Có để tính số giao dịch trong `[t − 24 giờ, t)`. "
        "Lấy trung vị số tiền từ tất cả các dòng trong bảng lịch sử của từng ca rồi chia số tiền hiện tại cho trung vị. "
        "Các mã giao dịch và ngày giúp tra cột `TRANSACTION_ID` trong từng tệp gốc `data/YYYY-MM-DD.pkl`. "
        "[Ánh xạ cột Handbook](handbook-sample.md#ánh-xạ-cột)",
        "",
        *histories,
        "## Chạy lại",
        "",
        "Chạy từ thư mục gốc repo sau khi cài thư viện trong `requirements.txt`.",
        "",
        "```powershell",
        "$handbookCheck = Join-Path $env:TEMP 'handbook-stage3-check.md'",
        "python scripts/analyze_handbook_stage3.py $handbookCheck",
        "```",
        "",
    ]
    args.output.write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()

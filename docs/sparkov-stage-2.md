# Sparkov · Chặng 2, mục 2.2

[Bảng Sparkov 183 ngày](../data/sparkov_183_days.csv.gz) có cùng bảy cột với Handbook: `dataset`, `transaction_id`, `timestamp`, `entity_id`, `amount`, `label`, `split`. Bảng dùng ánh xạ của [mẫu Chặng 1](sparkov-sample.md), giữ mã thẻ gốc dưới dạng chuỗi và sắp theo thời điểm rồi theo mã giao dịch.

| Tập | Từ ngày | Đến ngày | Số ngày | Giao dịch | Nhãn gian lận | Thiếu lịch sử 7 ngày |
|---|---|---|---:|---:|---:|---:|
| `train` | 2019-01-02 | 2019-04-01 | 90 | 174.016 | 1.523 | 1.017 |
| `validation` | 2019-04-02 | 2019-05-01 | 30 | 66.638 | 385 | 15 |
| `test` | 2019-05-02 | 2019-07-03 | 63 | 164.600 | 771 | 16 |
| **Tổng** | **2019-01-02** | **2019-07-03** | **183** | **405.254** | **2.679** | **1.048** |

[Thống kê theo ngày](../data/sparkov_daily_stats.csv) ghi số giao dịch, số nhãn gian lận và số dòng có `missing_history = 1` trong từng ngày của [lịch đã chốt ở Chặng 1](../data/sparkov_183_days.csv).

## Tái tạo bảng Sparkov

[Mã chuẩn hóa](../scripts/prepare_sparkov_stage2.py) đọc hai CSV từ [ZIP Sparkov trên Kaggle](https://www.kaggle.com/datasets/kartik2112/fraud-detection) và dùng lịch Chặng 1 để chọn ngày. Chạy từ thư mục gốc của repo bằng PowerShell. Bản bàn giao được tạo với Python 3.14.5, pandas 2.3.3 và NumPy 2.3.5.

```powershell
python -m pip install -r requirements.txt
$sparkovSource = Join-Path $env:TEMP 'sparkov-source.zip'
$sparkovCheck = Join-Path $env:TEMP 'sparkov-183-days-check.csv.gz'
$sparkovDailyCheck = Join-Path $env:TEMP 'sparkov-daily-stats-check.csv'
curl.exe --fail --location --output $sparkovSource https://www.kaggle.com/api/v1/datasets/download/kartik2112/fraud-detection
if ($LASTEXITCODE -ne 0) { throw 'Không tải được dữ liệu Sparkov.' }
python scripts/prepare_sparkov_stage2.py $sparkovSource $sparkovCheck $sparkovDailyCheck
if ($LASTEXITCODE -ne 0) { throw 'Không tạo được dữ liệu Sparkov.' }
python -c "import gzip, sys; from pathlib import Path; a, b, c, d = sys.argv[1:]; print(gzip.open(a, 'rb').read() == gzip.open(b, 'rb').read()); print(Path(c).read_text() == Path(d).read_text())" data/sparkov_183_days.csv.gz $sparkovCheck data/sparkov_daily_stats.csv $sparkovDailyCheck
```

Lệnh cuối so sánh nội dung hai bảng và in `True` cho mỗi bảng khớp.

## Áp dụng đặc trưng chung

Script gọi [`build_features`](../scripts/transaction_features.py) với bộ A+B trên toàn bộ 183 ngày để thống kê lịch sử của thẻ. [Từ điển đặc trưng](handbook-stage-2.md#từ-điển-đặc-trưng) mô tả các cột A và B. Khi dùng bảng cho mô hình, tính đặc trưng trên toàn bộ bảng rồi chọn dòng theo `split` để giữ lịch sử của cùng thẻ qua các ranh giới ngày. Bảng CSV.gz chứa dữ liệu chuẩn hóa để TV3 có thể chọn bộ đặc trưng khi chạy.

```python
import pandas as pd
from scripts.transaction_features import FEATURES_A, build_features

transactions = pd.read_csv(
    "data/sparkov_183_days.csv.gz",
    dtype={"transaction_id": "string", "entity_id": "string"},
)
features_ab = build_features(transactions, feature_set="A+B")
features_a = features_ab[list(FEATURES_A)]
validation_features = features_ab.loc[transactions["split"].eq("validation")]
```

## Kết quả kiểm tra

- Đối chiếu cả 405.254 dòng với ZIP nguồn theo mã giao dịch. Mã duy nhất trên cả ba tập, mỗi ngày trong lịch có giao dịch và mỗi ngày thuộc đúng một tập. Toàn bộ 1.118 dòng ngày 02/01 khớp CSV Chặng 1 theo sáu cột chung.
- Mã thẻ khớp nguyên văn với nguồn. Trong 936 mã thẻ có giao dịch, 908 mã xuất hiện trong cả ba tập.
- A+B trả về 10 cột cho từng giao dịch. Có 936 dòng chưa từng có giao dịch trước đó nên thiếu `seconds_since_previous`. Có 1.048 dòng thiếu `amount_to_median_7d`, khớp số dòng có cửa sổ 7 ngày rỗng. Số liệu theo từng ngày đã được đối chiếu với bảng chuẩn hóa và kết quả đặc trưng.

Hai giao dịch dưới đây được đối chiếu trực tiếp theo mã thẻ và ngày giờ. Giao dịch ngay trước mỗi dòng nằm ở tập liền trước.

| Tập | Giao dịch đầu ngày chia tập | Giao dịch trước đó cùng thẻ | Số giây từ giao dịch trước |
|---|---|---|---:|
| `validation` | `d1da7bbca6e613f7484265bd21487ea1` | `9968ab0247ec20e11f26afb61949c40d` | 25.928 |
| `test` | `8ad757e967d98422c5bd3bb40015fd42` | `591771e99963c8003727c89c354ab23e` | 112.681 |

### Đối chiếu độc lập Sparkov

- Đọc lại hai CSV trong ZIP gốc đã đối chiếu SHA-256 với Chặng 1. Cả 405.254 mã giao dịch là duy nhất và khớp với nguồn về thời điểm, mã thẻ, số tiền và nhãn.
- Cả 183 ngày đều có giao dịch và thuộc đúng một trong ba tập 90/30/63 ngày theo lịch Chặng 1. Mẫu ngày đầu và toàn bộ 183 dòng thống kê theo ngày đều khớp.
- Giữ mã thẻ dưới dạng chuỗi trong toàn bộ phép đối chiếu. Trong 936 thẻ, 908 thẻ xuất hiện ở cả ba tập. Tính lại khoảng cách đến thời điểm liền trước theo mã thẻ cho toàn bộ giao dịch và thu được kết quả khớp với hàm A+B, gồm 25.928 giây qua ranh giới train/validation và 112.681 giây qua ranh giới validation/test.

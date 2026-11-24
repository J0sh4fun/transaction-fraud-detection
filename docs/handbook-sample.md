# transaction-fraud-detection

## Dữ liệu mẫu Handbook · Chặng 1, mục 1.1

[CSV ngày 01/04/2018](../data/samples/handbook_2018-04-01.csv) chứa toàn bộ giao dịch của ngày đầu tiên trong bộ dữ liệu mô phỏng gốc. Nguồn là [tệp `2018-04-01.pkl` của Fraud Detection Handbook](https://github.com/Fraud-Detection-Handbook/simulated-data-raw/blob/6e67dbd0a3bfe0d7ec33abc4bce5f37cd4ff0d6a/data/2018-04-01.pkl) tại commit `6e67dbd`. [Mô tả bộ mô phỏng và các cột nguồn](https://fraud-detection-handbook.github.io/fraud-detection-handbook/Chapter_3_GettingStarted/SimulatedDataset.html)

### Ánh xạ cột

| Cột nguồn | Cột chung | Quy ước |
| --- | --- | --- |
| Giá trị cố định | `dataset` | `handbook` |
| `TRANSACTION_ID` | `transaction_id` | Mã giao dịch gốc, dùng để đối chiếu. |
| `TX_DATETIME` | `timestamp` | Giữ ngày giờ mô phỏng đến giây theo dạng `YYYY-MM-DD HH:MM:SS`. Nguồn không có múi giờ. |
| `CUSTOMER_ID` | `entity_id` | Mã khách hàng. |
| `TX_AMOUNT` | `amount` | Số tiền gốc, ghi với hai chữ số thập phân. |
| `TX_FRAUD` | `label` | `1` là gian lận, `0` là giao dịch hợp lệ. |

Bốn cột nguồn ngoài bảng chung là `TERMINAL_ID`, `TX_TIME_SECONDS`, `TX_TIME_DAYS` và `TX_FRAUD_SCENARIO`.

### Tải và tạo lại CSV

Chạy từ thư mục gốc của repo trong PowerShell với Python 3.12. Lệnh tạo bản đối chiếu trong thư mục tạm.

```powershell
python -m pip install pandas==3.0.1
$handbookSource = Join-Path $env:TEMP "handbook-2018-04-01.pkl"
$handbookCheck = Join-Path $env:TEMP "handbook-2018-04-01-check.csv"
curl.exe --fail --location --output $handbookSource https://raw.githubusercontent.com/Fraud-Detection-Handbook/simulated-data-raw/6e67dbd0a3bfe0d7ec33abc4bce5f37cd4ff0d6a/data/2018-04-01.pkl
python scripts/prepare_handbook_sample.py $handbookSource $handbookCheck
$expected = Get-Content -Raw -LiteralPath "data/samples/handbook_2018-04-01.csv"
$regenerated = Get-Content -Raw -LiteralPath $handbookCheck
($expected -replace '\r\n', "`n") -ceq ($regenerated -replace '\r\n', "`n")
```

Script kiểm tra SHA-256 của nguồn trước khi đọc. Dòng cuối phải trả về `True`.

### Bằng chứng đối chiếu

| Chỉ số | Tệp gốc | CSV bàn giao |
| --- | ---: | ---: |
| Số giao dịch | 9.488 | 9.488 |
| Số giao dịch gian lận | 3 | 3 |
| Giao dịch sớm nhất | `2018-04-01 00:00:31` | `2018-04-01 00:00:31` |
| Giao dịch muộn nhất | `2018-04-01 23:59:51` | `2018-04-01 23:59:51` |

Đã đối chiếu toàn bộ 9.488 mã giao dịch duy nhất và các giá trị theo bảng ánh xạ. TV2 có thể kiểm tra nhanh giao dịch `3527` lúc `10:17:43`, có mã khách hàng `3774`, số tiền `225.41` và nhãn `1`.

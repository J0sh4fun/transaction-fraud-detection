# transaction-fraud-detection

## Dữ liệu mẫu Sparkov · Chặng 1, mục 1.2

[CSV ngày 02/01/2019](../data/samples/sparkov_2019-01-02.csv) chứa toàn bộ giao dịch trong ngày theo bảng cột chung. Nguồn là [Credit Card Transactions Fraud Detection Dataset](https://www.kaggle.com/datasets/kartik2112/fraud-detection) của kartik2112 trên Kaggle, giấy phép CC0. Script đọc cả hai tệp `fraudTrain.csv` và `fraudTest.csv` trong ZIP.

### Ánh xạ cột

| Cột nguồn | Cột chung | Quy ước |
| --- | --- | --- |
| Giá trị cố định | `dataset` | `sparkov` |
| `trans_num` | `transaction_id` | Mã giao dịch gốc, dùng để đối chiếu. |
| `trans_date_trans_time` | `timestamp` | Giữ ngày giờ trong nguồn đến giây theo dạng `YYYY-MM-DD HH:MM:SS`. |
| `cc_num` | `entity_id` | Mã thẻ mô phỏng. Khi nhập CSV vào bảng tính, đặt kiểu cột này là văn bản để giữ nguyên mọi chữ số. |
| `amt` | `amount` | Giá trị số tiền gốc. |
| `is_fraud` | `label` | `1` là gian lận, `0` là giao dịch hợp lệ. |

### Chọn 183 ngày

Nguồn có 1.852.394 giao dịch, từ `2019-01-01 00:00:18` đến `2020-12-31 23:59:34` theo ngày giờ trong tệp gốc. Quy ước chọn các ngày có trọn khoảng từ 00:00 đến trước 00:00 hôm sau nằm trong khoảng quan sát của cả hai tệp. Mốc đầu tiên là 18 giây sau nửa đêm, nên quy ước này bắt đầu từ 02/01/2019.

[Danh sách 183 ngày](../data/sparkov_183_days.csv) chạy liên tục từ 02/01 đến 03/07/2019 và mọi ngày đều có giao dịch. Ngày mẫu là ngày đầu tiên trong danh sách có đủ hai loại nhãn.

### Tải và tạo lại CSV

Chạy từ thư mục gốc của repo trong PowerShell với Python 3.12 trở lên. Lệnh tải ZIP gốc và tạo hai bản đối chiếu trong thư mục tạm.

```powershell
$sparkovSource = Join-Path $env:TEMP "sparkov-source.zip"
$sparkovSampleCheck = Join-Path $env:TEMP "sparkov-sample-check.csv"
$sparkovDaysCheck = Join-Path $env:TEMP "sparkov-days-check.csv"
curl.exe --fail --location --output $sparkovSource https://www.kaggle.com/api/v1/datasets/download/kartik2112/fraud-detection
if ($LASTEXITCODE -ne 0) { throw "Không tải được ZIP Sparkov." }
python scripts/prepare_sparkov_sample.py $sparkovSource $sparkovSampleCheck $sparkovDaysCheck
if ($LASTEXITCODE -ne 0) { throw "Không tạo được CSV Sparkov." }
$expectedSample = Get-Content -Raw -LiteralPath "data/samples/sparkov_2019-01-02.csv"
$regeneratedSample = Get-Content -Raw -LiteralPath $sparkovSampleCheck
$expectedDays = Get-Content -Raw -LiteralPath "data/sparkov_183_days.csv"
$regeneratedDays = Get-Content -Raw -LiteralPath $sparkovDaysCheck
($expectedSample -replace '\r\n', "`n") -ceq ($regeneratedSample -replace '\r\n', "`n")
($expectedDays -replace '\r\n', "`n") -ceq ($regeneratedDays -replace '\r\n', "`n")
```

Hai dòng cuối phải trả về `True`. SHA-256 của ZIP dùng để tạo bản bàn giao là `4e32829b9ba5a6b17af707c513c15204011044df0e8971e431cedca3d8c0a8a1`.

### Bằng chứng đối chiếu

| Chỉ số ngày 02/01/2019 | Tệp gốc | CSV bàn giao |
| --- | ---: | ---: |
| Số giao dịch | 1.118 | 1.118 |
| Số giao dịch gian lận | 7 | 7 |
| Số giao dịch hợp lệ | 1.111 | 1.111 |
| Giao dịch sớm nhất | `2019-01-02 00:04:32` | `2019-01-02 00:04:32` |
| Giao dịch muộn nhất | `2019-01-02 23:59:24` | `2019-01-02 23:59:24` |

Đã đối chiếu đủ 1.118 mã giao dịch duy nhất và các giá trị theo bảng ánh xạ. Có thể truy về dòng nguồn bằng cặp cột `transaction_id` trong mẫu và `trans_num` trong tệp gốc.

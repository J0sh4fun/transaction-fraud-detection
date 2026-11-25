# Handbook và đặc trưng dùng chung · Chặng 2, mục 2.1

[Bảng Handbook 183 ngày](../data/handbook_183_days.csv.gz) gồm bảy cột `dataset`, `transaction_id`, `timestamp`, `entity_id`, `amount`, `label`, `split`. Bảng dùng cùng ánh xạ cột với [mẫu Chặng 1](handbook-sample.md), được sắp theo thời điểm rồi theo mã giao dịch. `entity_id` là mã khách hàng trên Handbook và mã thẻ trên Sparkov.

| Tập | Từ ngày | Đến ngày | Số ngày | Giao dịch | Nhãn gian lận |
|---|---|---|---:|---:|---:|
| `train` | 2018-04-01 | 2018-06-29 | 90 | 863.006 | 6.761 |
| `validation` | 2018-06-30 | 2018-07-29 | 30 | 287.364 | 2.532 |
| `test` | 2018-07-30 | 2018-09-30 | 63 | 603.785 | 5.388 |
| **Tổng** | **2018-04-01** | **2018-09-30** | **183** | **1.754.155** | **14.681** |

## Tái tạo bảng Handbook

[Mã chuẩn hóa](../scripts/prepare_handbook_stage2.py) đọc 183 tệp ngày từ [kho dữ liệu gốc của Handbook](https://github.com/Fraud-Detection-Handbook/simulated-data-raw), ghim cùng commit với Chặng 1. Script xác minh SHA-256 của bản tải trước khi đọc các tệp pickle, kiểm tra ngày và mã giao dịch duy nhất trên toàn bộ bảng.

Chạy từ thư mục gốc của repo bằng PowerShell. Bản bàn giao được tạo với Python 3.13.5, pandas 2.2.3 và NumPy 2.5.5.

```powershell
python -m pip install -r requirements.txt
$handbookSource = Join-Path $env:TEMP 'handbook-6e67dbd.tar.gz'
$handbookCheck = Join-Path $env:TEMP 'handbook-183-days-check.csv.gz'
curl.exe --fail --location --output $handbookSource https://codeload.github.com/Fraud-Detection-Handbook/simulated-data-raw/tar.gz/6e67dbd0a3bfe0d7ec33abc4bce5f37cd4ff0d6a
if ($LASTEXITCODE -ne 0) { throw 'Không tải được dữ liệu Handbook.' }
python scripts/prepare_handbook_stage2.py $handbookSource $handbookCheck
```

SHA-256 của tệp CSV.gz bàn giao là `a529dc8007fa01451da7088fbd7272aa9405c32b7adf45efa69ca0bebaddbcb6`.

## Từ điển đặc trưng

[Hàm `build_features`](../scripts/transaction_features.py) trả về bảng đặc trưng cùng chỉ mục và thứ tự dòng với bảng đầu vào. Có thể dùng danh sách `FEATURES_A` và `FEATURES_B` để chọn cột. Hãy truyền các tập cùng một lượt, rồi dùng cột `split` của bảng gốc để lấy từng tập. Lịch sử của validation và test được nối qua ranh giới chia tập theo khóa `(dataset, entity_id)`.

| Bộ | Cột | Cách tính |
|---|---|---|
| A | `log_amount` | Logarit tự nhiên của `1 + amount`. |
| A | `hour_sin`, `hour_cos` | Sin và cos của `2π × (giờ + phút/60) / 24`, theo quy ước Chặng 1. |
| A | `dow_sin`, `dow_cos` | Sin và cos của `2π × thứ / 7`, với thứ Hai bằng 0. |
| B | `count_1h`, `count_24h` | Số giao dịch của cùng khách hàng hoặc thẻ trong `[t − 1 giờ, t)` và `[t − 24 giờ, t)`. |
| B | `seconds_since_previous` | Số giây từ giao dịch gần nhất có thời điểm nhỏ hơn `t`. Ghi `NaN` khi chưa từng quan sát giao dịch trước đó. |
| B | `amount_to_median_7d` | Số tiền hiện tại chia trung vị số tiền trong `[t − 7 ngày, t)`. Ghi `NaN` khi cửa sổ rỗng hoặc trung vị bằng 0. |
| B | `missing_history` | Bằng 1 khi cửa sổ 7 ngày rỗng, bằng 0 khi có giao dịch trong cửa sổ. |

Các cửa sổ lấy cả giao dịch ở cận dưới. Hai giao dịch tại cùng thời điểm `t` dùng chung lịch sử trước `t`. Cột `label` không tham gia tính đặc trưng.

```python
import pandas as pd
from scripts.transaction_features import build_features

transactions = pd.read_csv(
    "data/handbook_183_days.csv.gz",
    dtype={"transaction_id": "string", "entity_id": "string"},
)
features = build_features(transactions, feature_set="A+B")
validation_features = features.loc[transactions["split"].eq("validation")]
```

Để dùng cho Sparkov, truyền bảng chuẩn hóa theo cùng lược đồ. Đọc `entity_id` dưới dạng chuỗi để giữ nguyên mã thẻ.

## Kết quả kiểm tra

Chạy `python scripts/check_stage2_features.py` để đối chiếu chương trình với ví dụ tính tay. Khách hàng Handbook `01` có giao dịch lần lượt tại `23/06 00:00` (10), `29/06 00:00` (20), `29/06 23:00` (30) và hai giao dịch `29/06 23:30` (40, 60). Tại `30/06 00:00`, giao dịch đầu tiên của validation có số tiền 90 và dùng trung vị 30 từ năm giao dịch train, kể cả giao dịch đúng cận 7 ngày.

Các cột kết quả dưới đây lần lượt là số giao dịch trong 1 giờ, số giao dịch trong 24 giờ, số giây từ giao dịch trước, tỷ lệ so với trung vị 7 ngày và cờ thiếu lịch sử.

| Ca kiểm tra | Tính tay | Chương trình |
|---|---|---|
| Khách hàng mới tại `30/06 00:00` | 0, 0, NaN, NaN, 1 | 0, 0, NaN, NaN, 1 |
| Giao dịch 40 tại `29/06 23:30` | 1, 2, 1.800, 2, 0 | 1, 2, 1.800, 2, 0 |
| Giao dịch 60 tại `29/06 23:30` | 1, 2, 1.800, 3, 0 | 1, 2, 1.800, 3, 0 |
| Giao dịch 90 đầu validation | 3, 4, 1.800, 3, 0 | 3, 4, 1.800, 3, 0 |
| Giao dịch 20 của thẻ Sparkov `01` tại `30/06 00:00` sau một giao dịch 5 lúc `23:45` | 1, 1, 900, 4, 0 | 1, 1, 900, 4, 0 |
| Giao dịch đầu test của khách hàng Handbook `01`, sau giao dịch validation 30 ngày | 0, 0, 2.592.000, NaN, 1 | 0, 0, 2.592.000, NaN, 1 |

Phép kiểm tra thêm một giao dịch ngày 31/07 với số tiền 1.000.000 xác nhận mọi đặc trưng của các dòng trước đó giữ nguyên. Năm cột A cũng khớp khi tính riêng và khi tính cùng B.

Bảng bàn giao có đủ 183 ngày liên tiếp, mã giao dịch duy nhất và toàn bộ giao dịch ngày 01/04 khớp mẫu đã duyệt ở Chặng 1. Hàm A+B chạy thành công trên toàn bộ 1.754.155 giao dịch Handbook và 1.118 giao dịch mẫu Sparkov, trả về 10 cột đặc trưng cho mỗi giao dịch.

### Đối chiếu độc lập của TV2

Tính lại năm cột B từ bảng Handbook theo mã khách hàng, chỉ dùng các giao dịch có thời điểm nhỏ hơn thời điểm đang xét. Kết quả khớp với hàm chung. Tỷ lệ so với trung vị trong bảng dưới được làm tròn đến sáu chữ số thập phân.

| Ca kiểm tra | Mã giao dịch | Số giao dịch 1 giờ | Số giao dịch 24 giờ | Số giây từ giao dịch trước | Tỷ lệ so với trung vị 7 ngày | Thiếu lịch sử |
|---|---|---:|---:|---:|---:|---:|
| Khách hàng mới | `0` | 0 | 0 | NaN | NaN | 1 |
| Hai giao dịch cùng thời điểm | `97797` | 0 | 4 | 11.615 | 1,656229 | 0 |
| Hai giao dịch cùng thời điểm | `97798` | 0 | 4 | 11.615 | 1,940706 | 0 |
| Giao dịch đầu tiên của validation | `863006` | 0 | 3 | 11.533 | 1,600320 | 0 |

Thêm một giao dịch tương lai có số tiền 1.000.000 của một trong các khách hàng được đối chiếu. Cả 10 đặc trưng của 2.076 giao dịch trước đó thuộc các khách hàng được kiểm tra đều giữ nguyên.

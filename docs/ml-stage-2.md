# Quy trình tiền xử lý theo từng mô hình · Chặng 2, mục 2.3 (TV3)

Tài liệu này bàn giao hai danh sách đặc trưng **A** và **A+B**, quy trình tiền xử lý theo từng thuật toán, cơ chế chặn rò rỉ dữ liệu và bằng chứng kiểm tra kích thước / giá trị thiếu trước và sau xử lý.

## Hai danh sách đặc trưng (Allow-list)

Cài đặt tại [`src/ml/preprocessing.py`](../src/ml/preprocessing.py). Khi TV1 chốt tên cột chính thức ở mục 2.1, chỉ cần truyền tham số `column_mapping` mà không phải sửa logic mô hình.

### Bộ A (5 đặc trưng)

| Tên cột chuẩn | Ý nghĩa |
| --- | --- |
| `log_amount` | Logarit số tiền giao dịch (`log1p(amount)`) |
| `hour_sin`, `hour_cos` | Biểu diễn chu kỳ giờ trong ngày |
| `dow_sin`, `dow_cos` | Biểu diễn chu kỳ ngày trong tuần |

### Bộ A+B (10 đặc trưng = Bộ A + 5 đặc trưng lịch sử)

| Tên cột chuẩn | Ý nghĩa |
| --- | --- |
| `tx_count_1h` | Số giao dịch của thực thể trong 1 giờ trước |
| `tx_count_24h` | Số giao dịch của thực thể trong 24 giờ trước |
| `time_since_last_tx` | Thời gian từ giao dịch gần nhất (`NaN` nếu khách hàng mới) |
| `amount_to_7d_median` | Tỷ lệ số tiền hiện tại so với trung vị 7 ngày trước (`NaN` nếu thiếu lịch sử 7 ngày) |
| `missing_history_flag` | Cờ thiếu lịch sử (`1` = thiếu lịch sử, `0` = có lịch sử) |

### Chặn rò rỉ cột không phải đặc trưng

Hàm `select_feature_frame()` chỉ chọn đúng danh sách allow-list và hàm `validate_feature_columns()` chặn cứng (báo lỗi `ValueError`) nếu bất kỳ cột nào sau đây xuất hiện trong danh sách đầu vào: `label`, `tx_fraud`, `is_fraud`, `transaction_id`, `entity_id`, `customer_id`, `card_id`, `cc_num`, `terminal_id`, `timestamp`, `tx_datetime`, `dataset`, `date`, `split`, `tx_fraud_scenario`, `fraud_scenario`, `scenario`.

## Quy trình tiền xử lý theo từng mô hình

Mọi phép học tham số (`SimpleImputer`, `StandardScaler`) đều đặt bên trong `scikit-learn Pipeline` và **chỉ `fit` trên tập `train`**.

| Thuật toán | Đặc trưng liên tục | Cờ nhị phân (`missing_history_flag`) | Lý do |
| --- | --- | --- | --- |
| `logistic_regression` | `SimpleImputer(strategy="median")` → `StandardScaler()` | `SimpleImputer(strategy="constant", fill_value=1.0)` (giữ nguyên 0/1) | Mô hình tuyến tính không nhận `NaN` và cần chuẩn hóa thang đo cho điều chuẩn L2 (`C`). |
| `isolation_forest` | `SimpleImputer(strategy="median")` | `SimpleImputer(strategy="constant", fill_value=1.0)` | Mô hình cây bất biến theo thang đo đơn điệu, chỉ cần điền `NaN` bằng trung vị tập `train`. |
| `hist_gradient_boosting` | Ép kiểu `float64`, **giữ nguyên `NaN` gốc** | `SimpleImputer(strategy="constant", fill_value=1.0)` | `HistGradientBoostingClassifier` học nhánh rẽ cho giá trị thiếu trực tiếp (native NaN handling). |

## Lệnh chạy kiểm tra tái lập

Chạy từ thư mục gốc của repo (mặc định dùng bộ dữ liệu giả lập 183 ngày chia `90 / 30 / 63`, hoặc truyền `--input <file.csv>` khi có dữ liệu thật từ TV1/TV2):

```powershell
$stage2Check = Join-Path $env:TEMP "ml-stage2-report-check.csv"
python scripts/verify_preprocessing_stage2.py --report $stage2Check
$expected = Get-Content -Raw -LiteralPath "data/samples/ml_stage2_preprocessing_report.csv"
$regenerated = Get-Content -Raw -LiteralPath $stage2Check
($expected -replace '\r\n', "`n") -ceq ($regenerated -replace '\r\n', "`n")
```

Dòng cuối phải trả về `True`.

## Bằng chứng kiểm tra điều kiện đạt (TV4 đối chiếu)

1. **Chỉ học tham số trên `train` (`train_only_fit_verified = true`):** Đã kiểm tra bằng cách thay đổi cực đoan dữ liệu `val` thành `1e9` và xác nhận `imputer.statistics_`, `scaler.mean_`, `scaler.scale_` giữ nguyên tuyệt đối.
2. **Chặn nhãn, mã định danh và kịch bản gian lận (`all_forbidden_samples_rejected = true`):** Dữ liệu đầu vào thử nghiệm có sẵn `label`, `transaction_id`, `entity_id`, `TX_FRAUD_SCENARIO`, `TERMINAL_ID`; không cột nào lọt vào ma trận đặc trưng và `validate_feature_columns()` từ chối tất cả các cột cấm.
3. **Khách hàng mới (cold-start) vẫn chấm được điểm hữu hạn:** Giao dịch mới với `tx_count_1h = 0`, `tx_count_24h = 0`, `time_since_last_tx = NaN`, `amount_to_7d_median = NaN`, `missing_history_flag = 1` trả về điểm hữu hạn trên đủ 6 tổ hợp:
   - `isolation_forest` (A / A+B): `0.080154` / `0.063552`
   - `logistic_regression` (A / A+B): `0.048995` / `0.012875`
   - `hist_gradient_boosting` (A / A+B): `0.017536` / `0.994313`
4. **Bảng kích thước đầu vào và số giá trị thiếu trước/sau xử lý:** Xem đầy đủ 18 dòng tại [`data/samples/ml_stage2_preprocessing_report.csv`](../data/samples/ml_stage2_preprocessing_report.csv). Tóm tắt cho bộ **A+B** (10 đặc trưng):

| Thuật toán | Tập | Số dòng | Số cột vào / ra | Thiếu trước xử lý | Thiếu sau xử lý | Điểm hữu hạn |
| --- | --- | ---: | :---: | ---: | ---: | :---: |
| `isolation_forest` | train / val / test | 1.080 / 360 / 756 | 10 / 10 | 234 / 86 / 208 | 0 / 0 / 0 | Đạt |
| `logistic_regression` | train / val / test | 1.080 / 360 / 756 | 10 / 10 | 234 / 86 / 208 | 0 / 0 / 0 | Đạt |
| `hist_gradient_boosting` | train / val / test | 1.080 / 360 / 756 | 10 / 10 | 234 / 86 / 208 | 234 / 86 / 208 (native NaN) | Đạt |

# Quy trình tiền xử lý theo từng mô hình · Chặng 2, mục 2.3 (TV3)

Tài liệu này bàn giao hai danh sách đặc trưng **A** và **A+B**, quy trình tiền xử lý theo từng thuật toán, cơ chế chặn rò rỉ dữ liệu và bảng kích thước / giá trị thiếu trước và sau xử lý trên cả hai bộ dữ liệu 183 ngày chính thức (**Handbook** và **Sparkov**).

## Hai danh sách đặc trưng (Allow-list)

Cài đặt tại [`src/ml/preprocessing.py`](../src/ml/preprocessing.py), khớp trực tiếp với `FEATURES_A` và `FEATURES_B` trong [`scripts/transaction_features.py`](../scripts/transaction_features.py).

### Bộ A (5 đặc trưng)

| Tên cột | Ý nghĩa |
| --- | --- |
| `log_amount` | Logarit tự nhiên của `1 + amount` |
| `hour_sin`, `hour_cos` | Biểu diễn chu kỳ giờ trong ngày |
| `dow_sin`, `dow_cos` | Biểu diễn chu kỳ ngày trong tuần |

### Bộ A+B (10 đặc trưng = Bộ A + 5 đặc trưng lịch sử)

| Tên cột | Ý nghĩa |
| --- | --- |
| `count_1h` | Số giao dịch của cùng thực thể trong `[t − 1 giờ, t)` |
| `count_24h` | Số giao dịch của cùng thực thể trong `[t − 24 giờ, t)` |
| `seconds_since_previous` | Số giây từ giao dịch gần nhất trước `t` (`NaN` nếu chưa có giao dịch trước đó) |
| `amount_to_median_7d` | Tỷ lệ số tiền hiện tại chia trung vị 7 ngày trước (`NaN` nếu cửa sổ 7 ngày rỗng hoặc trung vị bằng 0) |
| `missing_history` | Cờ thiếu lịch sử 7 ngày (`1` = rỗng, `0` = có lịch sử) |

### Chặn rò rỉ cột không phải đặc trưng

Hàm `select_feature_frame()` chỉ chọn đúng danh sách allow-list và hàm `validate_feature_columns()` chặn cứng (`ValueError`) nếu bất kỳ cột cấm nào xuất hiện: `label`, `tx_fraud`, `is_fraud`, `transaction_id`, `entity_id`, `customer_id`, `card_id`, `cc_num`, `terminal_id`, `timestamp`, `tx_datetime`, `dataset`, `date`, `split`, `tx_fraud_scenario`, `fraud_scenario`, `scenario`.

## Quy trình tiền xử lý theo từng mô hình

Mọi phép học tham số (`SimpleImputer`, `StandardScaler`) đều nằm trong `scikit-learn Pipeline` và **chỉ `fit` trên tập `train`** (90 ngày đầu). Không mở hay tính bất kỳ chỉ số hiệu năng nào trên tập `test`.

| Thuật toán | Đặc trưng liên tục | Cờ nhị phân (`missing_history`) | Lý do |
| --- | --- | --- | --- |
| `logistic_regression` | `SimpleImputer(strategy="median")` → `StandardScaler()` | `SimpleImputer(strategy="constant", fill_value=1.0)` (giữ nguyên 0/1) | Mô hình tuyến tính không nhận `NaN` và cần chuẩn hóa thang đo cho điều chuẩn L2 (`C`). |
| `isolation_forest` | `SimpleImputer(strategy="median")` | `SimpleImputer(strategy="constant", fill_value=1.0)` | Mô hình cây bất biến theo thang đo đơn điệu, chỉ cần điền `NaN` bằng trung vị tập `train`. |
| `hist_gradient_boosting` | Ép kiểu `float64`, **giữ nguyên `NaN` gốc** | `SimpleImputer(strategy="constant", fill_value=1.0)` | `HistGradientBoostingClassifier` học nhánh rẽ trực tiếp cho giá trị thiếu (native NaN handling). |

## Lệnh chạy kiểm tra tái lập

Chạy từ thư mục gốc của repo (đọc trực tiếp `data/handbook_183_days.csv.gz` và `data/sparkov_183_days.csv.gz`, gọi `scripts/transaction_features.py::build_features`):

```powershell
$stage2Check = Join-Path $env:TEMP "ml-stage2-report-check.csv"
python scripts/verify_preprocessing_stage2.py --report $stage2Check
$expected = Get-Content -Raw -LiteralPath "data/samples/ml_stage2_preprocessing_report.csv"
$regenerated = Get-Content -Raw -LiteralPath $stage2Check
($expected -replace '\r\n', "`n") -ceq ($regenerated -replace '\r\n', "`n")
```

Dòng cuối phải trả về `True`.

## Bằng chứng kiểm tra điều kiện đạt (TV4 đối chiếu)

1. **Khớp từ điển đặc trưng (`matches_transaction_features_py = true`):** `FEATURE_SET_A == FEATURES_A` và `FEATURE_SET_B_EXTRA == FEATURES_B`.
2. **Chỉ học tham số trên `train` (`train_only_fit_verified = true` trên cả 2 nguồn):** Thay đổi cực đoan dữ liệu `validation` thành `1e9` và xác nhận `imputer.statistics_`, `scaler.mean_`, `scaler.scale_` không đổi tuyệt đối.
3. **Chặn nhãn, mã định danh và kịch bản gian lận (`all_forbidden_samples_rejected = true`):** `validate_feature_columns()` từ chối tất cả các cột cấm và chỉ cột trong `FEATURES_A` / `FEATURES_B` đi vào ma trận đầu vào.
4. **Khách hàng mới (cold-start) chấm được điểm hữu hạn trên cả 2 nguồn:** Giao dịch mới với `count_1h = 0`, `count_24h = 0`, `seconds_since_previous = NaN`, `amount_to_median_7d = NaN`, `missing_history = 1` trả về điểm hữu hạn trên đủ 6 tổ hợp:
   - **Handbook:**
     - `isolation_forest` (A / A+B): `0.023238` / `0.050009`
     - `logistic_regression` (A / A+B): `0.018321` / `0.012346`
     - `hist_gradient_boosting` (A / A+B): `0.007663` / `0.000516`
   - **Sparkov:**
     - `isolation_forest` (A / A+B): `0.029852` / `0.044008`
     - `logistic_regression` (A / A+B): `0.000986` / `0.000617`
     - `hist_gradient_boosting` (A / A+B): `0.000457` / `0.000212`
5. **Bảng kích thước đầu vào và số giá trị thiếu trước/sau xử lý:** Xem đầy đủ 36 dòng tại [`data/samples/ml_stage2_preprocessing_report.csv`](../data/samples/ml_stage2_preprocessing_report.csv).
   - Với **Bộ A** (5 đặc trưng): cả Handbook và Sparkov có `0` giá trị thiếu trước và sau xử lý trên cả 3 tập (`5 → 5` cột).
   - Với **Bộ A+B** (10 đặc trưng, `10 → 10` cột, không phát sinh `inf`):

| Nguồn | Thuật toán | Số dòng (`train` / `validation` / `test`) | Thiếu trước xử lý | Thiếu sau xử lý |
| --- | --- | --- | --- | --- |
| `handbook` | `isolation_forest` | 863.006 / 287.364 / 603.785 | 12.030 / 769 / 1.716 | 0 / 0 / 0 |
| `handbook` | `logistic_regression` | 863.006 / 287.364 / 603.785 | 12.030 / 769 / 1.716 | 0 / 0 / 0 |
| `handbook` | `hist_gradient_boosting` | 863.006 / 287.364 / 603.785 | 12.030 / 769 / 1.716 | 12.030 / 769 / 1.716 (native NaN) |
| `sparkov` | `isolation_forest` | 174.016 / 66.638 / 164.600 | 1.947 / 20 / 17 | 0 / 0 / 0 |
| `sparkov` | `logistic_regression` | 174.016 / 66.638 / 164.600 | 1.947 / 20 / 17 | 0 / 0 / 0 |
| `sparkov` | `hist_gradient_boosting` | 174.016 / 66.638 / 164.600 | 1.947 / 20 / 17 | 1.947 / 20 / 17 (native NaN) |

*(Trên Sparkov, tổng số giá trị thiếu trước xử lý `1.947 + 20 + 17 = 1.984` khớp chính xác với báo cáo mục 2.2: `936` dòng thiếu `seconds_since_previous` + `1.048` dòng thiếu `amount_to_median_7d`.)*

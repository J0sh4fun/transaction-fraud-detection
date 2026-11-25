# Huấn luyện thử 3 thuật toán ML · Chặng 1, mục 1.3 (TV3)

Tài liệu này bàn giao môi trường Python, chương trình huấn luyện thử và bảng điểm mẫu cho ba thuật toán ứng viên: **Isolation Forest**, **Logistic Regression** và **HistGradientBoosting**.

## Phiên bản môi trường đã kiểm chứng

Tệp khai báo thư viện: [`requirements.txt`](../requirements.txt).

| Thành phần | Phiên bản đã kiểm chứng | Khai báo trong `requirements.txt` |
| --- | --- | --- |
| Python | `3.11.9` | Python `>=3.11` |
| `numpy` | `2.4.6` | `numpy>=2.0,<3` |
| `pandas` | `3.0.6` | `pandas>=2.2,<4` |
| `scikit-learn` | `1.9.1` | `scikit-learn>=1.6,<2` |

## Lệnh cài đặt và chạy tái lập

Chạy từ thư mục gốc của repo trong PowerShell:

```powershell
python -m pip install -r requirements.txt
$mlCheck = Join-Path $env:TEMP "ml-stage1-check.csv"
python scripts/smoke_test_models.py --output $mlCheck
$expected = Get-Content -Raw -LiteralPath "data/samples/ml_stage1_sample_scores.csv"
$regenerated = Get-Content -Raw -LiteralPath $mlCheck
($expected -replace '\r\n', "`n") -ceq ($regenerated -replace '\r\n', "`n")
```

Dòng cuối phải trả về `True` (cố định `seed = 42`).

## Dữ liệu mẫu và quy ước đầu ra

- Script [`scripts/smoke_test_models.py`](../scripts/smoke_test_models.py) tạo bảng giao dịch giả lập cố định gồm **200 dòng** theo đúng lược đồ chung (`dataset`, `transaction_id`, `timestamp`, `entity_id`, `amount`, `label`), chia theo thời gian:
  - Tập huấn luyện (`train`): **140 dòng** (14 gian lận, 126 hợp lệ).
  - Tập chấm thử (`eval`): **60 dòng** (6 gian lận, 54 hợp lệ).
- Đặc trưng thử nghiệm gồm 5 cột số học (`log_amount`, `hour_sin`, `hour_cos`, `dow_sin`, `dow_cos`).
- Bảng điểm bàn giao: [`data/samples/ml_stage1_sample_scores.csv`](../data/samples/ml_stage1_sample_scores.csv) gồm **180 dòng** (`60 giao dịch × 3 mô hình`), mỗi cặp `(transaction_id, algorithm)` là duy nhất.

## Kiểm tra chiều điểm `risk_score` (đặc biệt cho Isolation Forest)

Theo quy ước chung, **`risk_score` càng cao thì giao dịch càng được ưu tiên kiểm tra trước**:

- **Logistic Regression** và **HistGradientBoosting**: dùng xác suất lớp gian lận `predict_proba(X)[:, 1]`.
- **Isolation Forest**: trong `scikit-learn`, `decision_function(X)` trả về giá trị **âm hơn / nhỏ hơn** cho điểm bất thường. Do đó chương trình đổi dấu:
  $$\text{risk\_score} = -\text{decision\_function}(X)$$

### Bằng chứng kiểm tra chiều điểm Isolation Forest

| Trường hợp kiểm tra | `decision_function` gốc | `risk_score = -decision_function` |
| --- | ---: | ---: |
| Giao dịch bình thường (trung vị train) | `0.033470` | `-0.033470` |
| Ngoại lai cực trị (`log_amount` cao bất thường) | `-0.167055` | `0.167055` |
| Trung bình tập `eval` với `label = 0` | — | `0.071380` |
| Trung bình tập `eval` với `label = 1` | — | `0.150227` |

Kết quả xác nhận điểm ngoại lai và nhóm `label = 1` có `risk_score` cao hơn rõ rệt so với nhóm bình thường.

## Bằng chứng kiểm tra 3 mô hình trên tập `eval` (60 dòng)

| Thuật toán (`algorithm`) | Số điểm trả về | Toàn bộ hữu hạn (`isfinite`) | Min | Median | Max |
| --- | ---: | :---: | ---: | ---: | ---: |
| `isolation_forest` | 60 | Đạt | `0.014001` | `0.071475` | `0.182011` |
| `logistic_regression` | 60 | Đạt | `0.000101` | `0.003564` | `0.951495` |
| `hist_gradient_boosting` | 60 | Đạt | `0.000018` | `0.001337` | `0.972360` |

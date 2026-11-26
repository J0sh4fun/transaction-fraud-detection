# Chạy 24 ứng viên trên tập validation · Chặng 3, mục 3.3 (TV3)

Tài liệu này bàn giao nhật ký 24 lượt huấn luyện ứng viên (`seed = 42`) và 24 bảng điểm validation tương ứng cho hai nguồn **Handbook** và **Sparkov** để TV4 đánh giá và chọn 12 cấu hình ở mục 3.4.

## Thiết lập thí nghiệm

- **Tập huấn luyện:** 90 ngày đầu (`split = "train"`): `863.006` giao dịch Handbook và `174.016` giao dịch Sparkov.
- **Tập chấm điểm:** 30 ngày validation (`split = "validation"`): `287.364` giao dịch Handbook (`30` ngày, `2.532` gian lận) và `66.638` giao dịch Sparkov (`30` ngày, `385` gian lận).
- **Tập test (63 ngày cuối):** không mở, không huấn luyện và không chấm điểm ở chặng này.
- **Tạo đặc trưng & tiền xử lý:** gọi [`build_features`](../scripts/transaction_features.py) trên toàn bộ bảng 183 ngày theo thứ tự thời gian (giữ lịch sử liên tục qua ranh giới train/validation), sau đó tách `train` / `validation` và áp dụng pipeline tiền xử lý riêng từng mô hình tại [`src/ml/preprocessing.py`](../src/ml/preprocessing.py) (chỉ `fit` trên `train`).
- **Lưới 24 ứng viên** (`2 nguồn × 2 bộ đặc trưng A / A+B × 3 thuật toán × 2 giá trị siêu tham số`, `seed = 42`):
  - `isolation_forest`: `max_samples ∈ {256, 1024}` (`risk_score = -decision_function`)
  - `logistic_regression`: `C ∈ {0.1, 1.0}` (`risk_score = predict_proba[:, 1]`)
  - `hist_gradient_boosting`: `max_leaf_nodes ∈ {15, 31}` (`risk_score = predict_proba[:, 1]`)
- **Chế độ chạy:** chạy đủ **24/24 lượt đầy đủ (`mode = full`)**, không cần rút gọn. Script vẫn hỗ trợ cờ `--reduced` (`256`, `C=1`, `15` nút lá) theo phương án dự phòng trong kế hoạch.

## Đầu ra bàn giao

- **Chương trình chạy:** [`scripts/run_stage3_validation.py`](../scripts/run_stage3_validation.py)
- **Nhật ký 24 lượt chạy:** [`data/stage3_validation_runs.csv`](../data/stage3_validation_runs.csv) (ghi đủ `run_id`, `dataset`, `algorithm`, `feature_set`, `config`, `seed`, `train_rows`, `validation_rows`, `validation_days`, `train_seconds`, `score_seconds`, `min/median/max_score`, `all_finite`, `score_file` và `score_file_sha256`).
- **24 tệp bảng điểm validation:** lưu tại thư mục [`data/validation_scores/`](../data/validation_scores/) dưới dạng `.csv.gz` (tổng `52,04 MB`, mỗi tệp tối đa `2,83 MB`).
- **Cột trong mỗi tệp bảng điểm:** `dataset`, `date`, `transaction_id`, `timestamp`, `label`, `algorithm`, `feature_set`, `config`, `risk_score` — tương thích trực tiếp với [`scripts/evaluate_alerts_stage2.py`](../scripts/evaluate_alerts_stage2.py) của TV4.

## Lệnh chạy tái lập và kiểm tra với script đánh giá TV4

Chạy từ thư mục gốc của repo trong PowerShell:

```powershell
python scripts/run_stage3_validation.py
```

Kiểm tra nhanh một tệp điểm bằng [`scripts/evaluate_alerts_stage2.py`](../scripts/evaluate_alerts_stage2.py) của TV4:

```powershell
$tmpIn = Join-Path $env:TEMP "stage3-sample-in.csv"
$tmpOut = Join-Path $env:TEMP "stage3-sample-out.csv"
python -c "import gzip, sys; open(sys.argv[2], 'wb').write(gzip.open(sys.argv[1], 'rb').read())" data/validation_scores/sparkov__hist_gradient_boosting__a_plus_b__max_leaf_nodes_31.csv.gz $tmpIn
python scripts/evaluate_alerts_stage2.py $tmpIn $tmpOut
Import-Csv $tmpOut | Where-Object { $_.scope -eq 'period' -and $_.k -eq '50' } | Format-Table dataset, algorithm, days, alerts, true_positives, true_positives_per_day, precision, recall
```

## Tóm tắt nhật ký 24 lượt chạy

Toàn bộ 24 lượt đều trả về **đúng 1 điểm hữu hạn (`all_finite = True`)** cho từng giao dịch validation (`287.364` dòng/lượt trên Handbook, `66.638` dòng/lượt trên Sparkov), cùng tập giao dịch và không trùng khóa `transaction_id`.

| Nguồn | Bộ đặc trưng | Thuật toán | Cấu hình | Train (s) | Score (s) | Min | Median | Max |
| --- | :---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `handbook` | A | `isolation_forest` | `max_samples=256` | 2,292 | 1,627 | -0,030833 | 0,017165 | 0,196950 |
| `handbook` | A | `isolation_forest` | `max_samples=1024` | 2,764 | 2,039 | -0,041811 | 0,007873 | 0,205638 |
| `handbook` | A | `logistic_regression` | `C=0.1` | 1,359 | 0,117 | 0,000101 | 0,006387 | 0,165090 |
| `handbook` | A | `logistic_regression` | `C=1` | 1,253 | 0,111 | 0,000099 | 0,006378 | 0,166107 |
| `handbook` | A | `hist_gradient_boosting` | `max_leaf_nodes=15` | 3,489 | 0,311 | 0,003328 | 0,005548 | 0,953452 |
| `handbook` | A | `hist_gradient_boosting` | `max_leaf_nodes=31` | 3,255 | 0,272 | 0,003414 | 0,005585 | 0,963313 |
| `handbook` | A+B | `isolation_forest` | `max_samples=256` | 2,824 | 1,956 | -0,087971 | -0,031814 | 0,197062 |
| `handbook` | A+B | `isolation_forest` | `max_samples=1024` | 3,376 | 2,126 | -0,096597 | -0,043158 | 0,215671 |
| `handbook` | A+B | `logistic_regression` | `C=0.1` | 2,269 | 0,288 | 0,000169 | 0,006097 | 1,000000 |
| `handbook` | A+B | `logistic_regression` | `C=1` | 2,382 | 0,186 | 0,000168 | 0,006092 | 1,000000 |
| `handbook` | A+B | `hist_gradient_boosting` | `max_leaf_nodes=15` | 3,369 | 0,134 | 0,000000 | 0,005132 | 1,000000 |
| `handbook` | A+B | `hist_gradient_boosting` | `max_leaf_nodes=31` | 0,830 | 0,088 | 0,000000 | 0,005953 | 1,000000 |
| `sparkov` | A | `isolation_forest` | `max_samples=256` | 0,372 | 0,277 | -0,023783 | 0,023667 | 0,146762 |
| `sparkov` | A | `isolation_forest` | `max_samples=1024` | 0,559 | 0,304 | -0,026008 | 0,019145 | 0,149342 |
| `sparkov` | A | `logistic_regression` | `C=0.1` | 0,157 | 0,015 | 0,000002 | 0,000996 | 0,952278 |
| `sparkov` | A | `logistic_regression` | `C=1` | 0,153 | 0,015 | 0,000002 | 0,000946 | 0,955198 |
| `sparkov` | A | `hist_gradient_boosting` | `max_leaf_nodes=15` | 0,368 | 0,029 | 0,000052 | 0,000430 | 0,976441 |
| `sparkov` | A | `hist_gradient_boosting` | `max_leaf_nodes=31` | 0,455 | 0,043 | 0,000000 | 0,000114 | 0,998354 |
| `sparkov` | A+B | `isolation_forest` | `max_samples=256` | 0,455 | 0,292 | -0,087181 | -0,027855 | 0,185306 |
| `sparkov` | A+B | `isolation_forest` | `max_samples=1024` | 0,616 | 0,369 | -0,096159 | -0,045564 | 0,202616 |
| `sparkov` | A+B | `logistic_regression` | `C=0.1` | 0,231 | 0,027 | 0,000001 | 0,000994 | 0,953773 |
| `sparkov` | A+B | `logistic_regression` | `C=1` | 0,289 | 0,030 | 0,000001 | 0,000918 | 0,956524 |
| `sparkov` | A+B | `hist_gradient_boosting` | `max_leaf_nodes=15` | 0,471 | 0,046 | 0,000000 | 0,000308 | 1,000000 |
| `sparkov` | A+B | `hist_gradient_boosting` | `max_leaf_nodes=31` | 0,395 | 0,036 | 0,000001 | 0,000327 | 1,000000 |

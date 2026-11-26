# Huấn luyện lại 12 cấu hình khóa và chấm 63 ngày test · Chặng 5, mục 5.3 (TV3)

Sau khi cả bốn nhiệm vụ Chặng 4 (`4.1`–`4.4`) đều đạt nghiệm thu tại commit `2297c52`, TV3 đã huấn luyện lại toàn bộ **12 cấu hình đã khóa** trên 120 ngày đầu (`train + validation`) và xuất bảng điểm cho toàn bộ **63 ngày `test`** trên cả hai nguồn **Handbook** và **Sparkov** để TV1 (`5.1`), TV2 (`5.2`) và TV4 (`5.4`) sử dụng.

## Thông tin chạy chính thức và đối chiếu khóa

| Thành phần | Giá trị thực tế |
| --- | --- |
| Commit chạy chính thức | `2297c52` |
| Tệp cấu hình khóa | [`configs/final_models_stage4.json`](../configs/final_models_stage4.json) (`SHA-256: 1748fd9eca3754f7bcb3bfca5e673c05553210b520a86e38c1e087a0ab24777c`) |
| SHA-256 `data/handbook_183_days.csv.gz` | `a529dc8007fa01451da7088fbd7272aa9405c32b7adf45efa69ca0bebaddbcb6` (khớp) |
| SHA-256 `data/sparkov_183_days.csv.gz` | `b7eaabf5c72009d579a942705b62434a658b82c1bf6d75a1fe4ffb57a1895031` (khớp) |
| Môi trường chạy | Python `3.11.9`, `numpy==2.4.6`, `pandas==3.0.6`, `scikit-learn==1.9.1` |
| Seed cố định | `42` |
| Lệnh chạy chính thức | `python scripts/run_final_models.py --mode test --dataset all --confirm-stage4-approved` |

## Phạm vi dữ liệu huấn luyện và chấm test

- **Handbook:**
  - Huấn luyện (`train + validation`): `1.150.370` giao dịch (`2018-04-01..2018-07-29`, 120 ngày).
  - Chấm điểm (`test`): `603.785` giao dịch (`2018-07-30..2018-09-30`, 63 ngày).
- **Sparkov:**
  - Huấn luyện (`train + validation`): `240.654` giao dịch (`2019-01-02..2019-05-01`, 120 ngày).
  - Chấm điểm (`test`): `164.600` giao dịch (`2019-05-02..2019-07-03`, 63 ngày).

## Đầu ra bàn giao cho TV1, TV2 và TV4

- **Nhật ký 12 lượt chạy chính thức:** [`data/stage5_test_runs.csv`](../data/stage5_test_runs.csv)
- **12 tệp bảng điểm test:** lưu tại [`data/test_scores/`](../data/test_scores/) (tổng `57,73 MB`, tối đa `5,88 MB`/tệp), mỗi tệp gồm 9 cột `dataset, date, transaction_id, timestamp, label, algorithm, feature_set, config, risk_score` — tương thích trực tiếp với [`scripts/evaluate_alerts_stage2.py`](../scripts/evaluate_alerts_stage2.py).

## Nhật ký 12 lượt huấn luyện và chấm điểm test

Đã kiểm tra tự động toàn bộ 12 tệp: mọi cấu hình trong cùng nguồn chấm đúng cùng tập và cùng thứ tự `transaction_id`, đủ 63 ngày, không trùng khóa và không thiếu/không có điểm vô hạn (`all_finite = True`).

| Nguồn | Thuật toán | Đặc trưng | Cấu hình khóa | Train (s) | Score (s) | Số dòng test | Min | Median | Max |
| --- | --- | :---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `handbook` | `hist_gradient_boosting` | A | `max_leaf_nodes=15` | 3,306 | 0,354 | 603.785 | 0,003230 | 0,005784 | 0,989540 |
| `handbook` | `hist_gradient_boosting` | A+B | `max_leaf_nodes=15` | 1,544 | 0,276 | 603.785 | 0,000000 | 0,006133 | 1,000000 |
| `handbook` | `isolation_forest` | A | `max_samples=1024` | 2,664 | 3,732 | 603.785 | -0,035772 | 0,008730 | 0,200387 |
| `handbook` | `isolation_forest` | A+B | `max_samples=1024` | 3,502 | 4,101 | 603.785 | -0,096933 | -0,047190 | 0,228219 |
| `handbook` | `logistic_regression` | A | `C=0.1` | 1,347 | 0,138 | 603.785 | 0,000116 | 0,006655 | 0,327036 |
| `handbook` | `logistic_regression` | A+B | `C=1` | 2,221 | 0,249 | 603.785 | 0,000035 | 0,006266 | 1,000000 |
| `sparkov` | `hist_gradient_boosting` | A | `max_leaf_nodes=15` | 1,283 | 0,144 | 164.600 | 0,000041 | 0,000259 | 0,997985 |
| `sparkov` | `hist_gradient_boosting` | A+B | `max_leaf_nodes=15` | 0,547 | 0,074 | 164.600 | 0,000000 | 0,003227 | 1,000000 |
| `sparkov` | `isolation_forest` | A | `max_samples=1024` | 1,187 | 1,293 | 164.600 | -0,029713 | 0,016756 | 0,153129 |
| `sparkov` | `isolation_forest` | A+B | `max_samples=256` | 1,019 | 1,071 | 164.600 | -0,086854 | -0,023659 | 0,193806 |
| `sparkov` | `logistic_regression` | A | `C=0.1` | 0,295 | 0,042 | 164.600 | 0,000002 | 0,000831 | 0,966252 |
| `sparkov` | `logistic_regression` | A+B | `C=1` | 0,466 | 0,079 | 164.600 | 0,000001 | 0,000803 | 0,991943 |

## Kiểm tra nhanh tương thích với bộ đánh giá TV4

Đã chạy thử trực tiếp bằng [`scripts/evaluate_alerts_stage2.py`](../scripts/evaluate_alerts_stage2.py) ở `K = 50` trên cấu hình dẫn đầu (`hist_gradient_boosting`, `A+B`, `max_leaf_nodes=15`):

- **Handbook (63 ngày):** `3.150` cảnh báo, `1.515` ca đúng (`24,05` ca/ngày, Precision@50 = `0,480952`, Recall@50 = `0,281180`).
- **Sparkov (63 ngày):** `3.150` cảnh báo, `563` ca đúng (`8,94` ca/ngày, Precision@50 = `0,178730`, Recall@50 = `0,730220`).

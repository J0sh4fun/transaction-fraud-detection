# Khóa cấu hình, lệnh huấn luyện lại 120 ngày và chạy thử · Chặng 4, mục 4.3 (TV3)

Tài liệu này bàn giao tệp cấu hình 12 mô hình đã khóa, lệnh chạy theo thứ tự để huấn luyện lại trên 120 ngày đầu (`train + validation`) và chấm 63 ngày cuối (`test`), cùng nhật ký chạy thử trên cửa sổ lịch sử thuộc `train + validation` (**không chạm tập `test`**).

## Phiên bản mã, dữ liệu và thư viện đã khóa

| Thành phần | Giá trị khóa |
| --- | --- |
| Base commit trên `main` | `687b2a8` |
| Tệp cấu hình cuối | [`configs/final_models_stage4.json`](../configs/final_models_stage4.json) (`SHA-256: 1748fd9eca3754f7bcb3bfca5e673c05553210b520a86e38c1e087a0ab24777c`) |
| Nguồn chọn cấu hình (mục 3.4) | [`data/selected_configurations_stage3.csv`](../data/selected_configurations_stage3.csv) |
| Dữ liệu Handbook 183 ngày | `data/handbook_183_days.csv.gz` (`SHA-256: a529dc8007fa01451da7088fbd7272aa9405c32b7adf45efa69ca0bebaddbcb6`) |
| Dữ liệu Sparkov 183 ngày | `data/sparkov_183_days.csv.gz` (`SHA-256: b7eaabf5c72009d579a942705b62434a658b82c1bf6d75a1fe4ffb57a1895031`) |
| Python / Thư viện | Python `3.11.9`, `numpy==2.4.6`, `pandas==3.0.6`, `scikit-learn==1.9.1` |
| Seed cố định | `42` |

## 12 cấu hình đã khóa

Chương trình [`scripts/run_final_models.py`](../scripts/run_final_models.py) tự động đối chiếu từng dòng trong `configs/final_models_stage4.json` với `data/selected_configurations_stage3.csv` trước khi chạy; nếu sai lệch bất kỳ tham số hoặc `seed` nào sẽ dừng ngay với `AssertionError`.

| Nguồn | Thuật toán | Bộ đặc trưng | Tham số khóa | Seed | Lý do chọn (mục 3.4) |
| --- | --- | :---: | --- | ---: | --- |
| `handbook` | `hist_gradient_boosting` | A | `max_leaf_nodes=15` | 42 | `higher_fraud_found_per_day` |
| `handbook` | `hist_gradient_boosting` | A+B | `max_leaf_nodes=15` | 42 | `higher_fraud_found_per_day` |
| `handbook` | `isolation_forest` | A | `max_samples=1024` | 42 | `higher_fraud_found_per_day` |
| `handbook` | `isolation_forest` | A+B | `max_samples=1024` | 42 | `higher_fraud_found_per_day` |
| `handbook` | `logistic_regression` | A | `C=0.1` | 42 | `tie_smaller_parameter` |
| `handbook` | `logistic_regression` | A+B | `C=1` | 42 | `higher_fraud_found_per_day` |
| `sparkov` | `hist_gradient_boosting` | A | `max_leaf_nodes=15` | 42 | `higher_fraud_found_per_day` |
| `sparkov` | `hist_gradient_boosting` | A+B | `max_leaf_nodes=15` | 42 | `higher_fraud_found_per_day` |
| `sparkov` | `isolation_forest` | A | `max_samples=1024` | 42 | `higher_fraud_found_per_day` |
| `sparkov` | `isolation_forest` | A+B | `max_samples=256` | 42 | `higher_fraud_found_per_day` |
| `sparkov` | `logistic_regression` | A | `C=0.1` | 42 | `tie_smaller_parameter` |
| `sparkov` | `logistic_regression` | A+B | `C=1` | 42 | `higher_fraud_found_per_day` |

## Lệnh chạy theo thứ tự

### Bước 1 · Chạy thử luồng trên cửa sổ lịch sử `train + validation` (Chặng 4.3 — dùng cho TV4 nghiệm thu)

Huấn luyện trên **113 ngày đầu** của `train + validation` và chấm **7 ngày cuối của `validation`** (không mở hay đọc bất kỳ dòng nào của `split = "test"`):

```powershell
$dryDir = Join-Path $env:TEMP "stage4-dryrun-scores"
$dryLog = Join-Path $env:TEMP "stage4-dryrun-log.csv"
python scripts/run_final_models.py --mode dry-run --scores-dir $dryDir --log $dryLog
```

Kiểm tra nhanh bằng [`scripts/evaluate_alerts_stage2.py`](../scripts/evaluate_alerts_stage2.py):

```powershell
$tmpIn = Join-Path $env:TEMP "stage4-dryrun-in.csv"
$tmpOut = Join-Path $env:TEMP "stage4-dryrun-out.csv"
python -c "import gzip, sys; open(sys.argv[2], 'wb').write(gzip.open(sys.argv[1], 'rb').read())" data/samples/stage4_dry_run_scores/dryrun__handbook__hist_gradient_boosting__a_plus_b__max_leaf_nodes_15.csv.gz $tmpIn
python scripts/evaluate_alerts_stage2.py $tmpIn $tmpOut
Import-Csv $tmpOut | Where-Object { $_.scope -eq 'period' -and $_.k -eq '50' } | Format-Table dataset, algorithm, days, alerts, true_positives, true_positives_per_day, precision, recall
```

### Bước 2 · Lệnh khóa cho Chặng 5.3 (CHỈ chạy sau khi `4.1–4.4` đều `Đạt`)

Script có chốt bảo vệ: nếu gọi `--mode test` mà thiếu cờ `--confirm-stage4-approved`, chương trình tự từ chối chạy (`TEST_LOCK_GUARD_BLOCKED = True`). Khi cả nhóm mở Chặng 5, chạy lần lượt theo từng nguồn để bàn giao sớm cho TV1/TV2/TV4:

```powershell
# 1) Chấm 63 ngày test Handbook (xuất ngay cho TV1 và TV4)
python scripts/run_final_models.py --mode test --dataset handbook --confirm-stage4-approved --log data/stage5_test_runs_handbook.csv

# 2) Chấm 63 ngày test Sparkov (xuất cho TV2 và TV4)
python scripts/run_final_models.py --mode test --dataset sparkov --confirm-stage4-approved --log data/stage5_test_runs_sparkov.csv

# Hoặc chạy gộp cả 2 nguồn trong một lượt (xuất nhật ký chung data/stage5_test_runs.csv)
python scripts/run_final_models.py --mode test --dataset all --confirm-stage4-approved
```

## Nhật ký chạy thử (Dry-run 113 ngày → 7 ngày)

- **Nhật ký đầy đủ 12 lượt:** [`data/stage4_dry_run_log.csv`](../data/stage4_dry_run_log.csv)
- **12 bảng điểm chạy thử:** [`data/samples/stage4_dry_run_scores/`](../data/samples/stage4_dry_run_scores/) (tổng `6,07 MB`, tối đa `0,65 MB`/tệp).
- **Cửa sổ chạy thử (thuần `train + validation`, `0` dòng `test`):**
  - **Handbook:** huấn luyện `1.083.466` dòng (`2018-04-01..2018-07-22`, 113 ngày) → chấm `66.904` dòng (`2018-07-23..2018-07-29`, 7 ngày).
  - **Sparkov:** huấn luyện `224.767` dòng (`2019-01-02..2019-04-24`, 113 ngày) → chấm `15.887` dòng (`2019-04-25..2019-05-01`, 7 ngày).

| Nguồn | Thuật toán | Đặc trưng | Cấu hình khóa | Train (s) | Score (s) | Số dòng chấm | Hữu hạn |
| --- | --- | :---: | --- | ---: | ---: | ---: | :---: |
| `handbook` | `hist_gradient_boosting` | A | `max_leaf_nodes=15` | 5,556 | 0,072 | 66.904 | Đạt |
| `handbook` | `hist_gradient_boosting` | A+B | `max_leaf_nodes=15` | 3,068 | 0,059 | 66.904 | Đạt |
| `handbook` | `isolation_forest` | A | `max_samples=1024` | 3,128 | 0,455 | 66.904 | Đạt |
| `handbook` | `isolation_forest` | A+B | `max_samples=1024` | 5,727 | 0,464 | 66.904 | Đạt |
| `handbook` | `logistic_regression` | A | `C=0.1` | 1,547 | 0,032 | 66.904 | Đạt |
| `handbook` | `logistic_regression` | A+B | `C=1` | 2,826 | 0,049 | 66.904 | Đạt |
| `sparkov` | `hist_gradient_boosting` | A | `max_leaf_nodes=15` | 1,472 | 0,032 | 15.887 | Đạt |
| `sparkov` | `hist_gradient_boosting` | A+B | `max_leaf_nodes=15` | 1,814 | 0,045 | 15.887 | Đạt |
| `sparkov` | `isolation_forest` | A | `max_samples=1024` | 1,294 | 0,116 | 15.887 | Đạt |
| `sparkov` | `isolation_forest` | A+B | `max_samples=256` | 0,978 | 0,111 | 15.887 | Đạt |
| `sparkov` | `logistic_regression` | A | `C=0.1` | 0,356 | 0,013 | 15.887 | Đạt |
| `sparkov` | `logistic_regression` | A+B | `C=1` | 0,540 | 0,022 | 15.887 | Đạt |

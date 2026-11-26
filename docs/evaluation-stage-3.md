# Đánh giá validation và chọn cấu hình · Mục 3.4 (TV4)

- [Bảng điểm validation](../data/validation_scorecard_stage3.csv) gồm 24 lượt chạy và 2 dòng đối chứng theo số tiền.
- [12 cấu hình được chọn](../data/selected_configurations_stage3.csv) gồm một dòng cho mỗi nguồn, thuật toán và bộ đặc trưng. Mỗi dòng ghi cấu hình còn lại, số ca của cả hai và lý do chọn.
- [Nhật ký và bảng điểm từng giao dịch do TV3 bàn giao](https://github.com/J0sh4fun/transaction-fraud-detection/tree/63ddff7fdf78657eb9605422afa30ee37a36849f/data) ở commit `63ddff7`. Hai bảng kết quả giữ thời gian huấn luyện và chấm điểm từ nhật ký này.

## Cách đánh giá

Chỉ sử dụng 30 ngày validation của mỗi nguồn. Đối chứng xếp giảm dần theo `amount`; các ứng viên xếp giảm dần theo `risk_score` đã xuất. Mỗi ngày chọn tối đa 50 giao dịch. Khi bằng điểm, ưu tiên `transaction_id` tăng dần theo quy tắc chặng 2. Precision@50 và Recall@50 lấy tổng các số đếm toàn kỳ.

Trong mỗi nhóm nguồn × thuật toán × bộ đặc trưng, chọn cấu hình có nhiều ca phát hiện trung bình/ngày hơn. Cả hai cấu hình cùng có 30 ngày, nên chương trình so sánh tổng số ca phát hiện để tránh hòa giả do làm tròn. Nếu tổng bằng nhau, chọn tham số nhỏ hơn. Báo cáo này dùng đủ 24 lượt và giữ nguyên điểm xuất của TV3. Quy trình không tính kết quả trên test.

## Kết quả ở K = 50

| Nguồn | Giao dịch validation | Đối chứng · ca đúng | Đối chứng · ca/ngày | Cấu hình đứng đầu trên validation | Ca đúng | Ca/ngày |
|---|---:|---:|---:|---|---:|---:|
| Handbook | 287.364 | 600 | 20,00 | HistGradientBoosting A+B, `max_leaf_nodes=15` | 737 | 24,57 |
| Sparkov | 66.638 | 247 | 8,23 | HistGradientBoosting A+B, `max_leaf_nodes=15` | 329 | 10,97 |

| Nguồn | Thuật toán | Đặc trưng | Cấu hình chọn | Ca đúng | Cấu hình còn lại | Ca đúng |
|---|---|---|---|---:|---|---:|
| Handbook | HistGradientBoosting | A | `max_leaf_nodes=15` | 587 | `max_leaf_nodes=31` | 570 |
| Handbook | HistGradientBoosting | A+B | `max_leaf_nodes=15` | 737 | `max_leaf_nodes=31` | 725 |
| Handbook | Isolation Forest | A | `max_samples=1024` | 27 | `max_samples=256` | 14 |
| Handbook | Isolation Forest | A+B | `max_samples=1024` | 80 | `max_samples=256` | 47 |
| Handbook | Logistic Regression | A | `C=0.1` | 598 | `C=1` | 598 |
| Handbook | Logistic Regression | A+B | `C=1` | 710 | `C=0.1` | 709 |
| Sparkov | HistGradientBoosting | A | `max_leaf_nodes=15` | 313 | `max_leaf_nodes=31` | 308 |
| Sparkov | HistGradientBoosting | A+B | `max_leaf_nodes=15` | 329 | `max_leaf_nodes=31` | 327 |
| Sparkov | Isolation Forest | A | `max_samples=1024` | 168 | `max_samples=256` | 145 |
| Sparkov | Isolation Forest | A+B | `max_samples=256` | 160 | `max_samples=1024` | 139 |
| Sparkov | Logistic Regression | A | `C=0.1` | 275 | `C=1` | 275 |
| Sparkov | Logistic Regression | A+B | `C=1` | 263 | `C=0.1` | 262 |

Hai trường hợp hòa đều thuộc Logistic Regression với bộ A. Cả Handbook và Sparkov chọn `C=0.1` theo quy tắc tham số nhỏ hơn. Mười nhóm còn lại chọn cấu hình có số ca đúng cao hơn.

## Nghiệm thu mục 3.3

Đã đối chiếu đủ 24 tổ hợp với seed `42` và mã SHA-256 của từng tệp. Mỗi lượt có đúng một điểm hữu hạn cho từng giao dịch chính thức thuộc validation của nguồn tương ứng. Từng mã giao dịch, ngày, thời điểm và nhãn đều khớp với dữ liệu đã chia tập. Tổng số điểm đối chiếu là **4.248.024**.

## Chạy lại

Chạy [script đánh giá](../scripts/evaluate_validation_stage3.py) từ thư mục gốc bằng Python 3.11 trở lên. Khi repo đã có `data/stage3_validation_runs.csv` và `data/validation_scores/`, dùng:

```powershell
$stage3Check = Join-Path $env:TEMP "tv4-stage3-check"
python scripts/evaluate_validation_stage3.py --output-dir $stage3Check
```

Nếu các tệp điểm đang ở một bản checkout riêng của nhánh TV3, thêm `--tv3-root <thư-mục-repo-TV3>`. Hai CSV xuất ra có cùng tên với hai bảng đã bàn giao ở đầu tài liệu.

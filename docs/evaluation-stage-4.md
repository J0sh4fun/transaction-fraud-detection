# Quy trình đánh giá test và mẫu kết quả · Mục 4.4 (TV4)

[Mẫu bảng kết quả test](../data/test_results_template_stage4.csv) có đúng 14 dòng. Mỗi nguồn có một dòng đối chứng theo số tiền và sáu tổ hợp của ba thuật toán với hai bộ đặc trưng A và A+B. Tham số và seed của 12 dòng ML lấy từ [cấu hình TV3 đã khóa](../configs/final_models_stage4.json), đối chiếu với [lựa chọn trên validation](../data/selected_configurations_stage3.csv). Các cột kết quả được để trống trước khi mở test. TV3 kiểm tra thứ tự và số lượng dòng khi duyệt mục 4.4.

## Xếp hạng giao dịch

Chấm riêng theo nguồn, cấu hình và ngày lịch. Xếp `risk_score` giảm dần với mô hình hoặc `amount` giảm dần với đối chứng. Khi bằng điểm, xếp `transaction_id` tăng dần theo giá trị số trên Handbook và theo thứ tự chuỗi trên Sparkov. Dùng trực tiếp điểm số do TV3 xuất, không làm tròn thêm khi xếp hạng. Với ngày có ít hơn K giao dịch, lấy toàn bộ giao dịch của ngày. Dùng cùng thứ tự xếp hạng cho cả bốn mức K để Top 50 luôn nằm trong Top 100.

## Định nghĩa các chỉ số

Gọi TP@K là số giao dịch trong Top K có `label = 1`, cộng qua 63 ngày test. Các công thức dưới đây tính riêng cho từng dòng trong mẫu.

| Cột trong mẫu | Cách tính |
|---|---|
| `test_days`, `fraud_total` | Số ngày được đánh giá và tổng số ca gian lận thực tế, kể cả ca ngoài danh sách cảnh báo. |
| `fraud_found_at_10`, `fraud_found_at_25`, `fraud_found_at_50`, `fraud_found_at_100` | Tổng TP@K ở từng mức ngân sách. |
| `fraud_found_per_day_at_50` | TP@50 / 63, tính cả ngày không có ca phát hiện. |
| `alerts_at_50` | Tổng số lượt rà soát thực tế, bằng tổng `min(50, số giao dịch trong ngày)`. |
| `precision_at_50` | TP@50 / `alerts_at_50`. |
| `recall_at_50` | TP@50 / `fraud_total`. |
| `extra_fraud_at_51_to_100` | TP@100 − TP@50, bằng số ca phát hiện thêm ở hạng 51–100. |

Precision và Recall được tính bằng tổng số đếm toàn kỳ. Nếu mẫu số bằng 0, ghi 0 theo quy ước chặng 2. Giữ nguyên số đếm và ghi tỷ lệ dưới dạng số từ 0 đến 1 trong CSV. Dùng [bộ đánh giá chặng 2](../scripts/evaluate_alerts_stage2.py) cho từng tệp cấu hình hoặc đối chứng. Kết quả ở từng K được lấy từ dòng `scope=period` của tệp đầu ra.

## Danh sách kiểm tra trước khi chấm test

- [ ] Các mục 4.1–4.4 đều `Đạt` trong [bảng tiến độ](progress.md) và cả nhóm xác nhận mới mở test.
- [ ] Xác nhận đúng hai tệp `data/handbook_183_days.csv.gz` và `data/sparkov_183_days.csv.gz`. Đối chiếu SHA-256 với mục `datasets` trong [cấu hình khóa](../configs/final_models_stage4.json). Đối chiếu ranh giới 120 ngày huấn luyện (`train` + `validation`) và 63 ngày test với phiếu [Sparkov](sparkov-stage-4.md) và [Handbook](handbook-stage-4.md).
- [ ] Kiểm tra đủ 12 tổ hợp đã khóa, tham số khớp [bảng chọn ở chặng 3](../data/selected_configurations_stage3.csv), seed `42` và mỗi nguồn có đủ 7 dòng trong mẫu.
- [ ] Ghi commit mã chạy và phiên bản Python, NumPy, pandas, scikit-learn của lượt chạy chính thức. Đối chiếu với [bản bàn giao 4.3 của TV3](ml-stage-4.md) trước khi chạy. Nếu thay đổi môi trường, ghi rõ phiên bản thực tế để có thể chạy lại.
- [ ] Cả nhóm thống nhất công thức, Top K theo ngày và quy tắc xử lý điểm hòa. Mỗi cấu hình phải xuất đúng một `risk_score` hữu hạn cho mỗi giao dịch test của nguồn tương ứng.
- [ ] Khi nhận điểm, đối chiếu mã giao dịch, ngày và nhãn với dữ liệu đã khóa. Chỉ điền kết quả sau khi số ngày, số giao dịch và tập mã giao dịch khớp giữa đối chứng và các mô hình trên cùng một nguồn.

## Đối chiếu chạy thử mục 4.3

TV4 chạy lại `scripts/run_final_models.py --mode dry-run` ở commit `f37a9df`. Cả 12 cấu hình và seed khớp bảng chọn của chặng 3. SHA-256 của hai bộ dữ liệu khớp tệp cấu hình khóa.

| Nguồn | Dòng huấn luyện trong 113 ngày | Dòng chấm trong 7 ngày validation mỗi cấu hình | Tổng điểm đối chiếu qua 6 cấu hình |
|---|---:|---:|---:|
| Handbook | 1.083.466 | 66.904 | 401.424 |
| Sparkov | 224.767 | 15.887 | 95.322 |

Tất cả 496.746 điểm hữu hạn và khớp bảng điểm bàn giao theo từng mã giao dịch. Lần đối chiếu dùng Python 3.12.4, NumPy 1.26.4, pandas 2.3.3 và scikit-learn 1.9.0 có sẵn trên máy TV4. Chỉ chạy chế độ `dry-run` trên train và validation.

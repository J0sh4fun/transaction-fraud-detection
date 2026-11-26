# Tiến độ dự án

Ngày 1–21 tính theo kế hoạch nhóm. Các mục chưa có thông tin trong repo được khởi tạo ở trạng thái `Chưa làm`. Người phụ trách cập nhật khi bắt đầu hoặc có bằng chứng mới.

Luồng trạng thái `Chưa làm → Đang làm → Chờ duyệt → Đạt`. Người duyệt ghi lỗi cụ thể và trả mục về `Đang làm` nếu kiểm tra thất bại. TV4 kiểm tra đủ bốn mục `Đạt` trước khi mở chặng tiếp theo.

| Mã | Nhiệm vụ | Người làm | Hạn | Liên kết đầu ra | Bằng chứng kiểm tra | Người duyệt | Trạng thái |
|---|---|---|---|---|---|---|---|
| 1.1 | Chuẩn hóa một ngày Handbook | TV1 | Ngày 3 | [Hướng dẫn và CSV](handbook-sample.md) | [Đối chiếu số dòng, nhãn và thời điểm](handbook-sample.md#bằng-chứng-đối-chiếu) | TV2 | Đạt |
| 1.2 | Xác định 183 ngày Sparkov và xuất ngày mẫu | TV2 | Ngày 3 | [Hướng dẫn và CSV](sparkov-sample.md) | [183 ngày liên tiếp](sparkov-sample.md#chọn-183-ngày), [đối chiếu ngày mẫu](sparkov-sample.md#bằng-chứng-đối-chiếu) | TV1 | Đạt |
| 1.3 | Chạy thử ba thuật toán trên dữ liệu nhỏ | TV3 | Ngày 3 | [Hướng dẫn chạy, mã nguồn và bảng điểm mẫu](ml-stage-1.md) | [Kiểm tra số lượng và tính hữu hạn của điểm](ml-stage-1.md#bằng-chứng-kiểm-tra-3-mô-hình-trên-tập-eval-60-dòng), [kiểm tra chiều điểm Isolation Forest](ml-stage-1.md#bằng-chứng-kiểm-tra-chiều-điểm-isolation-forest) | TV4 | Đạt |
| 1.4 | Lập bảng tiến độ và tạo danh sách cảnh báo theo số tiền | TV4 | Ngày 3 | [Mã xếp hạng và hai CSV cảnh báo](amount-baseline.md) | [Kết quả và truy vết](amount-baseline.md#kết-quả-kiểm-tra) | TV3 | Đạt |
| 2.1 | Chuẩn hóa Handbook và tạo đặc trưng A, A+B | TV1 | Ngày 7 | [Bảng 183 ngày, mã và từ điển đặc trưng](handbook-stage-2.md) | [Đối chiếu độc lập của TV2](handbook-stage-2.md#đối-chiếu-độc-lập-của-tv2) | TV2 | Đạt |
| 2.2 | Chuẩn hóa Sparkov, kiểm tra dữ liệu và tạo đặc trưng | TV2 | Ngày 7 | [Bảng 183 ngày, thống kê theo ngày và mã](sparkov-stage-2.md) | [Đối chiếu độc lập với dữ liệu gốc và lịch sử thẻ](sparkov-stage-2.md#đối-chiếu-độc-lập-sparkov) | TV1 | Đạt |
| 2.3 | Xây quy trình tiền xử lý cho từng mô hình | TV3 | Ngày 7 | — | — | TV4 | Chưa làm |
| 2.4 | Tính và kiểm tra các chỉ số đánh giá theo ngày | TV4 | Ngày 7 | — | — | TV3 | Chưa làm |
| 3.1 | Kiểm tra đặc trưng lịch sử trên Handbook | TV1 | Ngày 11 | — | — | TV2 | Chưa làm |
| 3.2 | Phân tích Sparkov và so sánh hai nguồn | TV2 | Ngày 11 | — | — | TV1 | Chưa làm |
| 3.3 | Chạy 24 ứng viên và xuất điểm validation | TV3 | Ngày 11 | — | — | TV4 | Chưa làm |
| 3.4 | Đánh giá validation và chọn 12 cấu hình | TV4 | Ngày 11 | — | — | TV3 | Chưa làm |
| 4.1 | Kiểm tra độc lập dữ liệu và đặc trưng Sparkov | TV1 | Ngày 14 | — | — | TV2 | Chưa làm |
| 4.2 | Kiểm tra độc lập dữ liệu và đặc trưng Handbook | TV2 | Ngày 14 | — | — | TV1 | Chưa làm |
| 4.3 | Chuẩn bị lệnh huấn luyện lại và chấm test | TV3 | Ngày 14 | — | — | TV4 | Chưa làm |
| 4.4 | Chốt quy trình đánh giá và mẫu bảng 14 dòng | TV4 | Ngày 14 | — | — | TV3 | Chưa làm |
| 5.1 | Phân tích kết quả và ca điển hình trên Handbook | TV1 | Ngày 17 | — | — | TV2 | Chưa làm |
| 5.2 | Phân tích kết quả Sparkov và đối chiếu hai nguồn | TV2 | Ngày 17 | — | — | TV1 | Chưa làm |
| 5.3 | Huấn luyện lại 12 cấu hình và chấm 63 ngày test | TV3 | Ngày 17 | — | — | TV4 | Chưa làm |
| 5.4 | Chạy đối chứng, tổng hợp 14 dòng và phân tích ngân sách | TV4 | Ngày 17 | — | — | TV3 | Chưa làm |
| 6.1 | Viết phần bài toán, dữ liệu và đặc trưng | TV1 | Ngày 21 | — | — | TV2 | Chưa làm |
| 6.2 | Viết phần phân tích lỗi và giới hạn dữ liệu | TV2 | Ngày 21 | — | — | TV1 | Chưa làm |
| 6.3 | Viết phần phương pháp và kiểm tra khả năng tái lập | TV3 | Ngày 21 | — | — | TV4 | Chưa làm |
| 6.4 | Ghép báo cáo, slide, notebook demo và tổng duyệt | TV4 | Ngày 21 | — | — | TV3 | Chưa làm |

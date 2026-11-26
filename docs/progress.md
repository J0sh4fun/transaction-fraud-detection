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
| 2.3 | Xây quy trình tiền xử lý cho từng mô hình | TV3 | Ngày 7 | [Quy trình tiền xử lý và đặc trưng A, A+B](https://github.com/J0sh4fun/transaction-fraud-detection/pull/8) | [Bản bàn giao kiểm tra trên dữ liệu Handbook và Sparkov](https://github.com/J0sh4fun/transaction-fraud-detection/commit/444f8c0) | TV4 | Đạt |
| 2.4 | Tính và kiểm tra các chỉ số đánh giá theo ngày | TV4 | Ngày 7 | [Script đánh giá và CSV tính tay](evaluation-stage-2.md) | [Đối chiếu các mức K và trường hợp bằng điểm](evaluation-stage-2.md#bằng-chứng-kiểm-tra) | TV3 | Đạt |
| 3.1 | Kiểm tra đặc trưng lịch sử trên Handbook | TV1 | Ngày 11 | [Phân bố train/validation và lịch sử giao dịch](handbook-stage-3.md) | [Đối chiếu độc lập của TV2](handbook-stage-3.md#đối-chiếu-độc-lập-của-tv2) | TV2 | Đạt |
| 3.2 | Phân tích Sparkov và so sánh hai nguồn | TV2 | Ngày 11 | [Bảng so sánh, báo cáo và hướng dẫn chạy lại](tv2-stage-3.md) | [Đối chiếu độc lập 240 dòng thống kê](tv2-stage-3.md#đối-chiếu-độc-lập) | TV1 | Đạt |
| 3.3 | Chạy 24 ứng viên và xuất điểm validation | TV3 | Ngày 11 | [Nhật ký 24 lượt chạy, mã và 24 bảng điểm validation](ml-stage-3.md) | [Tóm tắt 24 lượt chạy và kiểm tra tương thích script TV4](ml-stage-3.md#tóm-tắt-nhật-ký-24-lượt-chạy) | TV4 | Đạt |
| 3.4 | Đánh giá validation và chọn 12 cấu hình | TV4 | Ngày 11 | [Bảng điểm validation và 12 cấu hình chọn](evaluation-stage-3.md) | [Kết quả K = 50, ứng viên còn lại và quy tắc xử lý hòa](evaluation-stage-3.md#kết-quả-ở-k--50) | TV3 | Đạt |
| 4.1 | Kiểm tra độc lập dữ liệu và đặc trưng Sparkov | TV1 | Ngày 14 | [Phiếu kiểm tra và lệnh chạy lại](sparkov-stage-4.md) | [Hai ranh giới chia tập](sparkov-stage-4.md#đối-chiếu-hai-ranh-giới), [kiểm tra rò rỉ thời gian](sparkov-stage-4.md#kiểm-tra-rò-rỉ-thời-gian) | TV2 | Đạt |
| 4.2 | Kiểm tra độc lập dữ liệu và đặc trưng Handbook | TV2 | Ngày 14 | [Phiếu kiểm tra, danh sách cột và lệnh chạy lại](handbook-stage-4.md) | [Kết quả nghiệm thu dữ liệu, đầu vào mô hình và bảng điểm validation](handbook-stage-4.md#kết-quả-nghiệm-thu) | TV1 | Đạt |
| 4.3 | Chuẩn bị lệnh huấn luyện lại và chấm test | TV3 | Ngày 14 | [Cấu hình khóa, lệnh chạy và nhật ký chạy thử](ml-stage-4.md) | [TV4 chạy lại và đối chiếu 12 bảng điểm](evaluation-stage-4.md#đối-chiếu-chạy-thử-mục-43) | TV4 | Đạt |
| 4.4 | Chốt quy trình đánh giá và mẫu bảng 14 dòng | TV4 | Ngày 14 | [Mẫu 14 dòng và quy trình đánh giá](evaluation-stage-4.md) | [Định nghĩa chỉ số và checklist trước khi chấm test](evaluation-stage-4.md#danh-sách-kiểm-tra-trước-khi-chấm-test) | TV3 | Đạt |
| 5.1 | Phân tích kết quả và ca điển hình trên Handbook | TV1 | Ngày 17 | [Bảng chênh lệch 9 tuần và hướng dẫn tái lập](handbook-stage-5.md) | [Ba ca có mã, nhãn, thứ hạng và đặc trưng](handbook-stage-5.md#ba-ca-điển-hình) | TV2 | Chờ duyệt |
| 5.2 | Phân tích kết quả Sparkov và đối chiếu hai nguồn | TV2 | Ngày 17 | [Bảng 9 tuần, ba ca và so sánh hai nguồn](tv2-stage-5.md) | [Nghiệm thu bảng ngày, bảng tuần và ba ca Sparkov](tv2-stage-5.md#kết-quả-nghiệm-thu) | TV1 | Đạt |
| 5.3 | Huấn luyện lại 12 cấu hình và chấm 63 ngày test | TV3 | Ngày 17 | [Nhật ký 12 lượt và 12 bảng điểm test 63 ngày](ml-stage-5.md) | [Đối chiếu đủ 63 ngày, tập mã giao dịch và script TV4](ml-stage-5.md#nhật-ký-12-lượt-huấn-luyện-và-chấm-điểm-test) | TV4 | Chờ duyệt |
| 5.4 | Chạy đối chứng, tổng hợp 14 dòng và phân tích ngân sách | TV4 | Ngày 17 | — | — | TV3 | Chưa làm |
| 6.1 | Viết phần bài toán, dữ liệu và đặc trưng | TV1 | Ngày 21 | — | — | TV2 | Chưa làm |
| 6.2 | Viết phần phân tích lỗi và giới hạn dữ liệu | TV2 | Ngày 21 | — | — | TV1 | Chưa làm |
| 6.3 | Viết phần phương pháp và kiểm tra khả năng tái lập | TV3 | Ngày 21 | — | — | TV4 | Chưa làm |
| 6.4 | Ghép báo cáo, slide, notebook demo và tổng duyệt | TV4 | Ngày 21 | — | — | TV3 | Chưa làm |

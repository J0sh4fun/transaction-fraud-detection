# Phiếu kiểm tra độc lập Handbook · Chặng 4, mục 4.2

TV2 kiểm tra [bảng Handbook Stage 2](../data/handbook_183_days.csv.gz), tập trung vào khóa giao dịch, nhãn và vai trò của cột kịch bản gian lận. [Script kiểm tra](../scripts/audit_handbook_stage4.py) đọc bản nguồn tại commit `6e67dbd0a3bfe0d7ec33abc4bce5f37cd4ff0d6a` của [Fraud Detection Handbook](https://github.com/Fraud-Detection-Handbook/simulated-data-raw/tree/6e67dbd0a3bfe0d7ec33abc4bce5f37cd4ff0d6a).

## Đối chiếu dữ liệu

Script xác minh SHA-256 của toàn bộ tar.gz trước khi đọc pickle, rồi đối chiếu 183 tệp ngày với bảng chuẩn hóa theo mã giao dịch. Các trường đối chiếu là mã giao dịch, ngày giờ, mã khách hàng, số tiền và nhãn. Số tiền được đối chiếu theo hai chữ số thập phân đúng quy ước xuất CSV của Stage 2.

| Tập | Số ngày | Giao dịch | Nhãn gian lận |
|---|---:|---:|---:|
| Train | 90 | 863.006 | 6.761 |
| Validation | 30 | 287.364 | 2.532 |
| Test | 63 | 603.785 | 5.388 |
| Tổng | 183 | 1.754.155 | 14.681 |

Khóa `transaction_id` duy nhất trên toàn bộ bảng. Mỗi giao dịch khớp nhãn nguồn `TX_FRAUD` và thuộc đúng ngày, tập đã chốt. Tại nguồn, `TX_FRAUD_SCENARIO = 0` tương ứng nhãn 0, các mã 1, 2, 3 tương ứng nhãn 1. Script in số dòng theo từng cặp mã kịch bản và nhãn để đối chiếu.

| Kịch bản nguồn | Nhãn | Số giao dịch |
|---|---:|---:|
| 0 | 0 | 1.739.474 |
| 1 | 1 | 973 |
| 2 | 1 | 9.077 |
| 3 | 1 | 4.631 |

Toàn bộ phép kiểm tra chạy thành công với Python 3.14.5, pandas 2.3.3, NumPy 2.3.5 và scikit-learn 1.9.1. Không phát hiện sai lệch cần sửa trong dữ liệu, nhãn hoặc danh sách đặc trưng.

## Các cột đi vào mô hình

Đối chiếu [điểm vào huấn luyện Stage 3](../scripts/run_stage3_validation.py), [hàm đặc trưng chung](../scripts/transaction_features.py) và [pipeline tiền xử lý](../src/ml/preprocessing.py). Cả ba thuật toán sử dụng cùng danh sách cho mỗi bộ.

| Bộ | Các cột đầu vào |
|---|---|
| A | `log_amount`, `hour_sin`, `hour_cos`, `dow_sin`, `dow_cos` |
| A+B | Năm cột A cùng `count_1h`, `count_24h`, `seconds_since_previous`, `amount_to_median_7d`, `missing_history` |

Script tính đặc trưng trên train và validation, chọn cột bằng `select_feature_frame`, rồi tạo đúng pipeline bằng `build_model_pipeline`. Với từng thuật toán và từng bộ, script kiểm tra các cột được cấu hình trong bộ tiền xử lý và số cột sau biến đổi validation. Bộ A có 5 cột, A+B có 10 cột. Các tham số tiền xử lý được học từ train.

| Trường | Vai trò được kiểm tra |
|---|---|
| `label` / `TX_FRAUD` | Nhãn để huấn luyện Logistic Regression, HistGradientBoosting và đối chiếu kết quả đánh giá. Isolation Forest được fit bằng X. |
| `TX_FRAUD_SCENARIO` | Dùng trong script kiểm tra để đối chiếu ý nghĩa nhãn ở nguồn. Bảng chuẩn hóa gồm bảy cột và không xuất trường kịch bản. |
| `transaction_id` | Truy vết giao dịch, kiểm tra khóa và phá hòa khi xếp hạng. |
| `entity_id` | Gom lịch sử của khách hàng khi tạo đặc trưng. |
| `timestamp`, `split`, `dataset` | Tính cửa sổ lịch sử, chọn tập và xác định nguồn. |

Khi đảo toàn bộ nhãn và thêm cột `TX_FRAUD_SCENARIO = 999` vào đầu vào hàm đặc trưng, kết quả đặc trưng train/validation giữ nguyên. Khi chèn nhãn, kịch bản và mã giao dịch vào bảng ứng viên, hàm chọn cột vẫn trả đúng A/A+B. Bộ kiểm tra cột từ chối nhãn, kịch bản và các mã định danh nếu chúng được yêu cầu làm đặc trưng.

## Chạy lại

Chạy từ thư mục gốc repo bằng PowerShell sau khi cài `requirements.txt`.

```powershell
$handbookSource = Join-Path $env:TEMP 'handbook-6e67dbd.tar.gz'
curl.exe --fail --location --output $handbookSource https://codeload.github.com/Fraud-Detection-Handbook/simulated-data-raw/tar.gz/6e67dbd0a3bfe0d7ec33abc4bce5f37cd4ff0d6a
if ($LASTEXITCODE -ne 0) { throw 'Không tải được nguồn Handbook.' }
python scripts/audit_handbook_stage4.py $handbookSource
if ($LASTEXITCODE -ne 0) { throw 'Kiểm tra Handbook thất bại.' }
```

Script kết thúc bằng `All Handbook Stage 4 checks passed.` khi toàn bộ đối chiếu đạt. Kiểm tra dữ liệu gồm cả nhãn test theo nhiệm vụ 4.2. Phép kiểm tra pipeline dùng train và validation. Kết quả này là phiếu kiểm tra dữ liệu và đầu vào mô hình tại phiên bản repo đang bàn giao.

# Phiếu kiểm tra độc lập Sparkov · Chặng 4, mục 4.1

TV1 đối chiếu [bảng Sparkov Chặng 2](../data/sparkov_183_days.csv.gz) với ZIP gốc đã ghim SHA-256 ở [Chặng 1](sparkov-sample.md#tải-và-tạo-lại-csv). Bảng được kiểm tra có SHA-256 `b7eaabf5c72009d579a942705b62434a658b82c1bf6d75a1fe4ffb57a1895031`. Phạm vi là dữ liệu và đặc trưng lịch sử, chưa huấn luyện lại mô hình hay chấm điểm test.

| Tập | Khoảng ngày, gồm hai đầu | Số ngày | Giao dịch |
|---|---|---:|---:|
| Train | 02/01–01/04/2019 | 90 | 174.016 |
| Validation | 02/04–01/05/2019 | 30 | 66.638 |
| Test | 02/05–03/07/2019 | 63 | 164.600 |

Toàn bộ **405.254** mã giao dịch là duy nhất và khớp với ZIP gốc về thời điểm, mã thẻ, số tiền và nhãn. Cả 183 ngày đều có giao dịch, mỗi ngày thuộc một tập và đủ 183 dòng thống kê theo ngày đã được đối chiếu.

## Đối chiếu hai ranh giới

Chọn giao dịch đầu tiên của mỗi tập mới. Tra giao dịch liền trước bằng cùng mã thẻ và thời điểm nhỏ hơn thời điểm đang xét.

| Ranh giới | Giao dịch đầu tập mới | Giao dịch trước đó cùng thẻ |
|---|---|---|
| Train → validation | `d1da7bbca6e613f7484265bd21487ea1` lúc 02/04/2019 00:01:12 | `9968ab0247ec20e11f26afb61949c40d` lúc 01/04/2019 16:49:04 |
| Validation → test | `8ad757e967d98422c5bd3bb40015fd42` lúc 02/05/2019 00:00:03 | `591771e99963c8003727c89c354ab23e` lúc 30/04/2019 16:42:02 |

| Ranh giới | GD trong 1 giờ | GD trong 24 giờ | Giây từ GD trước | GD trong 7 ngày | Số tiền / trung vị 7 ngày | Cờ thiếu lịch sử |
|---|---:|---:|---:|---:|---:|---:|
| Train → validation | 0 | 3 | 25.928 | 10 | 118,16 / 31,72 = 3,725095 | 0 |
| Validation → test | 0 | 0 | 112.681 | 21 | 123,44 / 44,16 = 2,795290 | 0 |

## Kiểm tra rò rỉ thời gian

- Tính lại cả năm cột B cho từng giao dịch bằng cách sắp lịch sử theo thẻ, xác định các cửa sổ `[t − k, t)` rồi tính trung vị trực tiếp. Kết quả khớp với hàm chung trên toàn bộ 405.254 dòng, gồm 12 dòng có giao dịch cùng thẻ và cùng thời điểm.
- Tính lại A+B chỉ với train, rồi chỉ với train và validation. Toàn bộ đặc trưng của các dòng tương ứng khớp với khi tính trên cả 183 ngày.
- Tại mỗi giao dịch ranh giới, thêm một giao dịch cùng thẻ đúng thời điểm `t` và một giao dịch ở `t + 1 giây` với số tiền lớn. Cả 10 đặc trưng của giao dịch đang xét đều giữ nguyên.

**Lỗi phát hiện** · Không có sai lệch về dữ liệu, chia tập hoặc lịch sử thẻ trong các phép kiểm tra trên. Không có bản sửa dữ liệu hay đặc trưng cần đưa vào thí nghiệm validation.

## Chạy lại

Sau khi cài thư viện trong `requirements.txt` và tải ZIP theo [hướng dẫn Chặng 1](sparkov-sample.md#tải-và-tạo-lại-csv), chạy từ thư mục gốc repo.

```powershell
$sparkovSource = Join-Path $env:TEMP 'sparkov-source.zip'
python scripts/audit_sparkov_stage4.py $sparkovSource
```

[Mã kiểm tra](../scripts/audit_sparkov_stage4.py) in hai giao dịch ranh giới, số liệu lịch sử và kết quả kiểm tra.

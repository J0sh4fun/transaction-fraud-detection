# Phân tích kết quả Handbook · Chặng 5, mục 5.1

Phân tích sáu cấu hình đã khóa trên 63 ngày test Handbook, từ 30/07 đến 30/09/2018, gồm 603.785 giao dịch và 5.388 ca gian lận. Mỗi ngày lấy 50 điểm cao nhất và dùng mã giao dịch theo thứ tự số tăng dần khi bằng điểm. [Nguồn bảng điểm](ml-stage-5.md) · [Quy trình đánh giá](evaluation-stage-4.md)

## Chênh lệch theo chín tuần

Mỗi ô mô hình ghi số ca đúng của A / A+B và chênh lệch ca/ngày trong ngoặc. Chênh lệch bằng (ca đúng A+B − ca đúng A) chia số ngày. [Bảng theo ngày](../data/sparkov_stage5_daily.csv) · [Bảng tuần hai nguồn, lọc Handbook](../data/sparkov_stage5_weekly.csv)

| Tuần | Khoảng ngày | Gian lận thực tế | HistGradientBoosting | Isolation Forest | Logistic Regression |
| --- | --- | --- | --- | --- | --- |
| 1 | 2018-07-30 → 2018-08-05 | 627 | 156 / 194 (+5.428571) | 6 / 22 (+2.285714) | 159 / 182 (+3.285714) |
| 2 | 2018-08-06 → 2018-08-12 | 570 | 97 / 135 (+5.428571) | 12 / 22 (+1.428571) | 103 / 127 (+3.428571) |
| 3 | 2018-08-13 → 2018-08-19 | 601 | 137 / 166 (+4.142857) | 11 / 22 (+1.571429) | 138 / 153 (+2.142857) |
| 4 | 2018-08-20 → 2018-08-26 | 594 | 156 / 184 (+4.000000) | 12 / 15 (+0.428571) | 161 / 178 (+2.428571) |
| 5 | 2018-08-27 → 2018-09-02 | 614 | 152 / 174 (+3.142857) | 5 / 29 (+3.428571) | 152 / 158 (+0.857143) |
| 6 | 2018-09-03 → 2018-09-09 | 593 | 149 / 172 (+3.285714) | 12 / 27 (+2.142857) | 150 / 171 (+3.000000) |
| 7 | 2018-09-10 → 2018-09-16 | 612 | 134 / 174 (+5.714286) | 3 / 26 (+3.285714) | 135 / 166 (+4.428571) |
| 8 | 2018-09-17 → 2018-09-23 | 580 | 102 / 141 (+5.571429) | 8 / 18 (+1.428571) | 102 / 142 (+5.714286) |
| 9 | 2018-09-24 → 2018-09-30 | 597 | 157 / 175 (+2.571429) | 11 / 20 (+1.285714) | 156 / 164 (+1.142857) |

| Thuật toán | Ca đúng A | Ca đúng A+B | Ca/ngày A | Ca/ngày A+B | Chênh lệch ca/ngày |
| --- | --- | --- | --- | --- | --- |
| HistGradientBoosting | 1240 | 1515 | 19.682540 | 24.047619 | +4.365079 |
| Isolation Forest | 80 | 201 | 1.269841 | 3.190476 | +1.920635 |
| Logistic Regression | 1256 | 1441 | 19.936508 | 22.873016 | +2.936508 |

HistGradientBoosting A+B dẫn đầu trong sáu cấu hình Handbook, với 1.515 ca đúng. Cả ba thuật toán tìm được nhiều ca hơn với A+B trên 63 ngày. Logistic Regression dùng C khác nhau giữa hai bộ đặc trưng, nên chênh lệch phản ánh cả đặc trưng và cấu hình đã chọn.

## Ba ca điển hình

Dùng HistGradientBoosting với cùng cấu hình 15 nút lá. Chọn giao dịch đầu tiên theo ngày rồi theo hạng A+B cho từng nhóm. Ca bắt đúng và báo nhầm mới vào top 50 khi dùng A+B. Ca bỏ sót rời top 50 khi chuyển từ A sang A+B.

| Ca | Mã giao dịch | Thời điểm | Nhãn | Hạng A | Hạng A+B | Điểm A | Điểm A+B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bắt đúng thêm | `1156201` | 2018-07-30 13:28:37 | 1 | 2962 | 24 | 0.006110 | 0.710210 |
| Báo nhầm thêm | `1159877` | 2018-07-30 22:23:43 | 0 | 145 | 27 | 0.014737 | 0.474176 |
| Gian lận bị bỏ sót | `1164474` | 2018-07-31 11:31:32 | 1 | 12 | 61 | 0.532467 | 0.049475 |

| Mã giao dịch | Khách hàng | Số tiền | GD 1 giờ | GD 24 giờ | Giây từ GD trước | Số tiền / trung vị 7 ngày | Thiếu lịch sử |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `1156201` | `2755` | 73.65 | 0 | 3 | 5555 | 4.452842 | 0 |
| `1159877` | `1022` | 173.06 | 0 | 0 | 104843 | 3.466747 | 0 |
| `1164474` | `1841` | 228.07 | 0 | 0 | 235836 | 1.953992 | 0 |

Ba ca minh họa thay đổi thứ hạng quan sát được. Đặc trưng lịch sử được tính trên giao dịch trước thời điểm đang xét của cùng khách hàng. Dùng mã giao dịch để tra bảng Handbook chuẩn hóa hoặc cột `TRANSACTION_ID` trong tệp nguồn theo ngày. [Dữ liệu chuẩn hóa](../data/handbook_183_days.csv.gz) · [Từ điển đặc trưng](handbook-stage-2.md#từ-điển-đặc-trưng)

## Chạy lại

Chạy từ thư mục gốc repo sau khi cài thư viện trong `requirements.txt`.

```powershell
$handbookCheck = Join-Path $env:TEMP 'handbook-stage5-check.md'
python scripts/analyze_handbook_stage5.py $handbookCheck
```

## Đối chiếu độc lập của TV2

Đã tạo lại báo cáo và xác nhận khớp bản bàn giao sau khi chuẩn hóa xuống dòng. SHA-256 của sáu bảng điểm Handbook khớp nhật ký TV3. Tính lại số ca đúng trong top 50 theo ngày rồi cộng theo chín tuần, cả 54 giá trị của sáu cấu hình đều khớp bảng tuần. Với ba giao dịch `1156201`, `1159877`, `1164474`, đã đối chiếu nhãn và thứ hạng A/A+B bằng quy tắc xếp hạng dùng chung. Số giao dịch trong 1 giờ, 24 giờ, thời gian từ lần trước và tỷ lệ số tiền so với trung vị 7 ngày được tính độc lập từ lịch sử khách hàng và đều khớp.

# Phân tích Sparkov và so sánh hai nguồn · Chặng 5, mục 5.2

Phân tích dùng [12 bảng điểm test do TV3 bàn giao](ml-stage-5.md), lấy tối đa 50 giao dịch riêng từng ngày theo điểm giảm dần. Điểm hòa được phá bằng mã giao dịch tăng dần, so số trên Handbook và so chuỗi trên Sparkov, đúng quy tắc của TV4. Bộ A và A+B dùng cấu hình đã chọn trên validation và khóa tại Stage 4.

## Chênh lệch giữa A+B và A

[Bảng so sánh toàn kỳ](../data/sparkov_stage5_comparison.csv) ghi số ca đúng trong top 50 trên 63 ngày test.

| Nguồn | Thuật toán | Ca đúng A | Ca đúng A+B | Chênh lệch ca/ngày |
|---|---|---:|---:|---:|
| Handbook | HistGradientBoosting | 1.240 | 1.515 | +4,365079 |
| Handbook | Isolation Forest | 80 | 201 | +1,920635 |
| Handbook | Logistic Regression | 1.256 | 1.441 | +2,936508 |
| Sparkov | HistGradientBoosting | 566 | 563 | −0,047619 |
| Sparkov | Isolation Forest | 330 | 264 | −1,047619 |
| Sparkov | Logistic Regression | 490 | 466 | −0,380952 |

Chênh lệch ca/ngày bằng `(ca đúng A+B − ca đúng A) / số ngày`. Với các cấu hình đã khóa, mức tăng quan sát được trên Handbook không lặp lại trên Sparkov. Riêng HistGradientBoosting, Sparkov giảm 3 ca trong 63 ngày, tương ứng 0,047619 ca/ngày.

Handbook có 603.785 giao dịch và 5.388 ca gian lận, trung bình 9.583,89 giao dịch và 85,52 ca gian lận/ngày. Sparkov có 164.600 giao dịch và 771 ca gian lận, trung bình 2.612,70 giao dịch và 12,24 ca gian lận/ngày. Mỗi mô hình phát 3.150 cảnh báo trên mỗi nguồn. Số ca/ngày giữa hai nguồn cần được đọc cùng quy mô giao dịch và số gian lận thực tế.

So sánh này đánh giá hai bộ đặc trưng với cấu hình đã được chọn cho từng bộ. Isolation Forest trên Sparkov dùng `max_samples=1024` cho A và `256` cho A+B. Logistic Regression dùng `C=0.1` cho A và `C=1` cho A+B trên cả hai nguồn. Vì vậy, chênh lệch của các tổ hợp này chịu ảnh hưởng đồng thời của đặc trưng và cấu hình đã chọn. HistGradientBoosting dùng cùng `max_leaf_nodes=15` cho cả A và A+B.

## Chín tuần Sparkov

Tuần 1 bắt đầu từ ngày test đầu tiên 02/05/2019. Mỗi tuần có bảy ngày. Các ô thuật toán ghi `ca đúng A / ca đúng A+B`. [Bảng tuần cho cả hai nguồn](../data/sparkov_stage5_weekly.csv) chứa thêm chênh lệch ca/ngày và phạm vi ngày của từng tuần.

| Tuần | Khoảng ngày 2019 | Giao dịch | Gian lận thực tế | HistGradientBoosting A / A+B | Isolation Forest A / A+B | Logistic Regression A / A+B |
|---|---|---:|---:|---:|---:|---:|
| 1 | 02/05–08/05 | 15.702 | 65 | 51 / 47 | 26 / 23 | 44 / 43 |
| 2 | 09/05–15/05 | 15.757 | 81 | 59 / 62 | 31 / 31 | 45 / 41 |
| 3 | 16/05–22/05 | 15.744 | 139 | 102 / 112 | 68 / 48 | 92 / 94 |
| 4 | 23/05–29/05 | 18.981 | 100 | 71 / 73 | 39 / 31 | 60 / 59 |
| 5 | 30/05–05/06 | 19.695 | 64 | 49 / 43 | 28 / 19 | 40 / 40 |
| 6 | 06/06–12/06 | 19.734 | 56 | 38 / 38 | 23 / 22 | 32 / 27 |
| 7 | 13/06–19/06 | 19.831 | 83 | 55 / 53 | 32 / 27 | 51 / 44 |
| 8 | 20/06–26/06 | 19.604 | 72 | 49 / 46 | 26 / 15 | 46 / 38 |
| 9 | 27/06–03/07 | 19.552 | 111 | 92 / 89 | 57 / 48 | 80 / 80 |

HistGradientBoosting A+B tìm thêm ca ở tuần 2–4, hòa tuần 6 và giảm ở năm tuần còn lại. Tuần 3 có nhiều gian lận nhất với 139 ca, trong đó A bắt được 102 và A+B bắt được 112. Tổng thay đổi toàn kỳ bằng tổng thay đổi của chín tuần.

## Ba trường hợp Sparkov

[CSV ca điển hình](../data/sparkov_stage5_cases.csv) ghi mã thẻ dạng chuỗi, thời điểm, cấu hình, điểm, thứ hạng A và A+B cùng cả 10 đặc trưng. Các ca được chọn bằng quy tắc lặp lại được trên HistGradientBoosting A+B đã khóa: lấy giao dịch đầu tiên theo ngày rồi thứ hạng cho mỗi loại ca. Đây là ví dụ minh họa hành vi ở ngưỡng 50.

| Loại ca | Mã giao dịch | Thời điểm 02/05/2019 | Nhãn | Hạng A | Hạng A+B | Số tiền | GD 24 giờ trước | Số tiền / trung vị 7 ngày |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Bắt đúng | `320b215d66bc6553663f30fa054cabf9` | 01:37:38 | 1 | 4 | 1 | 1.082,36 | 3 | 16,070676 |
| Báo nhầm | `fe4e49afc2f5bf1311d583586eecd5e4` | 01:45:48 | 0 | 7 | 6 | 309,79 | 2 | 5,529989 |
| Gian lận bị bỏ sót | `db1c4c45796e44b2a2f12a179b1def34` | 03:36:32 | 1 | 70 | 143 | 262,04 | 5 | 2,938986 |

Ca bắt đúng nằm trong top 50 ở cả hai bộ. Ca báo nhầm có số tiền cao hơn trung vị lịch sử và được cả hai bộ ưu tiên, nhưng nhãn nguồn là 0. Ca bỏ sót có nhãn 1 và nằm ngoài top 50 ở cả hai bộ. Những quan sát này mô tả giao dịch và thứ hạng, chưa xác định đóng góp nhân quả của từng đặc trưng vào quyết định của mô hình.

## Chạy lại và kiểm tra

[Script phân tích](../scripts/analyze_sparkov_stage5.py) đọc điểm đã lưu, đối chiếu cấu hình với danh sách đã khóa và metadata với bảng nguồn, rồi xuất bốn CSV. [Bảng theo ngày](../data/sparkov_stage5_daily.csv) có 756 dòng, tương ứng 2 nguồn × 3 thuật toán × 2 bộ đặc trưng × 63 ngày. Bảng tuần có 54 dòng và bảng tổng hợp có 6 dòng. Các tuần của mỗi nguồn được tính từ ngày test đầu tiên của nguồn đó.

```powershell
$tv2Stage5Check = Join-Path $env:TEMP 'tv2-stage5-check'
python scripts/analyze_sparkov_stage5.py $tv2Stage5Check
```

Đã đối chiếu từng dòng kết quả ngày ở K=50 của cả 12 bảng điểm với `evaluate_alerts_stage2.py`. Ba thứ hạng được kiểm tra độc lập bằng quy tắc xếp hạng dùng chung, và số giao dịch 1 giờ, 24 giờ, thời gian từ lần giao dịch trước cùng tỷ lệ so với trung vị 7 ngày được tính lại từ lịch sử thẻ. Toàn bộ kiểm tra khớp. Ngưỡng cảnh báo được áp dụng riêng từng ngày và kết quả luôn nằm trong giới hạn số cảnh báo cũng như tổng gian lận thực tế.

## Kết quả nghiệm thu

Đã tái lập cả bốn CSV và xác nhận SHA-256 của 12 bảng điểm khớp nhật ký TV3. Tính lại số ca đúng bằng cách lấy 50 điểm cao nhất từng ngày sau khi sắp mã giao dịch, rồi cộng theo tuần. Cả 756 số đếm theo ngày và 54 dòng theo tuần đều khớp. Ba ca Sparkov khớp mã, ngày, nhãn, thứ hạng A/A+B và đặc trưng lịch sử tính từ giao dịch của cùng thẻ.

Tổng ca đúng A+B so với A tăng cho cả ba thuật toán trên Handbook và giảm cho cả ba trên Sparkov với các cấu hình đã khóa. Phần so sánh ghi rõ quy mô giao dịch, số ca gian lận theo ngày và khác biệt cấu hình giữa hai bộ đặc trưng.

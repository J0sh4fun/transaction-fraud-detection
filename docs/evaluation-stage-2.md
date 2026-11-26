# Đánh giá cảnh báo theo ngày · Mục 2.4 (TV4)

[Script đánh giá](../scripts/evaluate_alerts_stage2.py) nhận CSV gồm `dataset`, `transaction_id`, `timestamp`, `label` và `risk_score`. Có thể dùng `--score-column amount` để chạy đối chứng theo số tiền. Nếu CSV điểm có cột `algorithm`, chương trình tính riêng cho từng mô hình trong từng nguồn. Mỗi nguồn và mô hình có một dòng điểm cho mỗi giao dịch. Khi thử nhiều cấu hình hoặc bộ đặc trưng của một mô hình, chạy riêng từng cấu hình trên cùng tập giao dịch.

## Cách tính

- Trong từng ngày, sắp điểm giảm dần và chọn tối đa K giao dịch với K bằng 10, 25, 50 và 100. Khi bằng điểm, ưu tiên mã giao dịch tăng dần, so theo số trên Handbook và theo chuỗi trên Sparkov.
- **Số ca đúng** (`true_positives`) là số cảnh báo có `label = 1`.
- **Precision@K** bằng số ca đúng chia cho số cảnh báo thực tế. Ngày có ít giao dịch hơn K dùng số cảnh báo thực tế làm mẫu số.
- **Recall@K** bằng số ca đúng chia cho tổng số gian lận thực tế, kể cả các giao dịch ngoài top K. Khi mẫu số bằng 0, ghi `0` và giữ cột `fraud_total` để nhận biết trường hợp đó.
- Dòng `scope=period` cộng số đếm qua các ngày rồi mới tính Precision và Recall. `true_positives_per_day` bằng tổng số ca đúng chia số ngày có trong đầu vào, kể cả ngày có giao dịch nhưng không có gian lận.

## Chạy lại

Chạy từ thư mục gốc bằng Python 3. [CSV tính tay](../data/samples/evaluation_stage2_example.csv) có 62 giao dịch giả lập trong ba ngày.

```powershell
$metricsCheck = Join-Path $env:TEMP "evaluation-stage2-check.csv"
python scripts/evaluate_alerts_stage2.py data/samples/evaluation_stage2_example.csv $metricsCheck
Import-Csv $metricsCheck | Where-Object scope -eq 'period' | Format-Table k, alerts, true_positives, precision, recall
```

## Bằng chứng kiểm tra

Ngày 1 có 55 giao dịch. Các mã `1`, `12`, `26`, `50`, `55` có nhãn 1. Hai mã `50` và `51` cùng điểm `0.51` tại ranh giới top 50. Mã `50` có nhãn 1 và được chọn trước mã `51`. Ngày 2 có 4 giao dịch với 2 ca gian lận. Ngày 3 có 3 giao dịch và không có gian lận. Hai ngày cuối lấy toàn bộ giao dịch ở cả bốn mức K.

### Kết quả theo ngày tại K = 50

| Ngày | Giao dịch | Gian lận thực tế | Cảnh báo | Ca đúng tính tay | Ca đúng từ CSV | Precision@50 | Recall@50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2020-01-01 | 55 | 5 | 50 | 4 | 4 | 4/50 | 4/5 |
| 2020-01-02 | 4 | 2 | 4 | 2 | 2 | 2/4 | 2/2 |
| 2020-01-03 | 3 | 0 | 3 | 0 | 0 | 0/3 | 0 |

### Kết quả toàn kỳ

| K | Cảnh báo tính tay / chương trình | Ca đúng tính tay / chương trình | Ca đúng/ngày | Precision@K tính tay | Precision@K từ CSV | Recall@K tính tay | Recall@K từ CSV |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 17 / 17 | 3 / 3 | 1,000000 | 3/17 | 0,176471 | 3/7 | 0,428571 |
| 25 | 32 / 32 | 4 / 4 | 1,333333 | 4/32 | 0,125000 | 4/7 | 0,571429 |
| 50 | 57 / 57 | 6 / 6 | 2,000000 | 6/57 | 0,105263 | 6/7 | 0,857143 |
| 100 | 62 / 62 | 7 / 7 | 2,333333 | 7/62 | 0,112903 | 7/7 | 1,000000 |

Khi nghiệm thu, TV3 có thể đảo thứ tự dòng trong CSV thử và kiểm tra kết quả vẫn như trên. Để chạy đối chứng trên dữ liệu mẫu chặng 1, dùng một CSV đầu vào chứa toàn bộ giao dịch của ngày, chẳng hạn `data/samples/handbook_2018-04-01.csv`, với tùy chọn `--score-column amount`.

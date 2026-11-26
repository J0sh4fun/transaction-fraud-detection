# So sánh Handbook và Sparkov · Chặng 3, mục 3.2

[Bảng thống kê theo ngày](../data/stage3_daily_comparison.csv) có 240 dòng, gồm 90 ngày train và 30 ngày validation của mỗi nguồn. Số liệu lấy từ hai bảng Stage 2. [Handbook](handbook-stage-2.md) · [Sparkov](sparkov-stage-2.md)

| Nguồn | Tập | Số ngày | Tổng giao dịch | Tổng ca gian lận | Giao dịch/ngày | Ca gian lận/ngày | Tỷ lệ gian lận | Thiếu lịch sử 7 ngày | Tỷ lệ kiểm tra ở mức 50 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Handbook | Train | 90 | 863.006 | 6.761 | 9.588,96 | 75,12 | 0,7834% | 0,8166% | 0,5214% |
| Handbook | Validation | 30 | 287.364 | 2.532 | 9.578,80 | 84,40 | 0,8811% | 0,2666% | 0,5220% |
| Sparkov | Train | 90 | 174.016 | 1.523 | 1.933,51 | 16,92 | 0,8752% | 0,5844% | 2,5860% |
| Sparkov | Validation | 30 | 66.638 | 385 | 2.221,27 | 12,83 | 0,5777% | 0,0225% | 2,2510% |

Các cột theo ngày trong bảng tóm tắt là trung bình trên số ngày của tập. Các tỷ lệ trong bảng dùng tổng số giao dịch làm mẫu số. Ví dụ, độ bao phủ validation của Sparkov là `(30 × 50) / 66.638 = 2,2510%`.

Sparkov có ít giao dịch mỗi ngày hơn Handbook. Vì vậy, ở validation cùng 50 lượt kiểm tra/ngày bao phủ **2,2510%** giao dịch Sparkov và **0,5220%** giao dịch Handbook. Tỷ lệ này đo phần giao dịch có thể được xem xét với ngân sách cho trước. Để biết trong số đó có bao nhiêu ca gian lận, cần có danh sách giao dịch được xếp hạng.

## Cách tính và đối chiếu

- Mỗi dòng CSV ứng với một nguồn, tập và ngày. `transactions` đếm tất cả giao dịch. `frauds` đếm các giao dịch có `label = 1`. `fraud_rate = frauds / transactions`.
- `missing_history` đếm các dòng có cờ thiếu lịch sử từ hàm A+B chung. Hàm xét cửa sổ `[t − 7 ngày, t)` của cùng khách hàng hoặc thẻ. Train và validation được truyền cùng một lượt để giữ lịch sử qua ranh giới chia tập. `missing_history_rate = missing_history / transactions`. [Từ điển đặc trưng](handbook-stage-2.md#từ-điển-đặc-trưng)
- `reviewed_at_50 = min(50, transactions)` và `review_rate_at_50 = reviewed_at_50 / transactions`. Ví dụ, mẫu Sparkov ngày 02/01/2019 có 1.118 giao dịch, trong đó 7 ca gian lận. Nếu rà soát 50 giao dịch, tỷ lệ bao phủ của ngày đó là `50 / 1.118 ≈ 4,47%`. [CSV mẫu Sparkov](../data/samples/sparkov_2019-01-02.csv)

## Chạy lại

Chạy từ thư mục gốc repo sau khi cài thư viện trong `requirements.txt`. Script đọc hai bảng CSV.gz Stage 2 và lọc train, validation trước khi tính đặc trưng.

```powershell
$stage3Check = Join-Path $env:TEMP 'stage3-daily-comparison-check.csv'
python scripts/analyze_stage3_datasets.py $stage3Check
$expected = Get-Content -Raw -LiteralPath 'data/stage3_daily_comparison.csv'
$regenerated = Get-Content -Raw -LiteralPath $stage3Check
($expected -replace '\r\n', "`n") -ceq ($regenerated -replace '\r\n', "`n")
```

Dòng cuối trả về `True` khi bảng tạo lại khớp bản bàn giao.

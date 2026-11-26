# Đặc trưng lịch sử Handbook · Chặng 3, mục 3.1

Dữ liệu lấy từ [bảng Handbook đã chia tập](../data/handbook_183_days.csv.gz). Tính A+B trên train và validation cùng lúc để giữ lịch sử qua ranh giới hai tập. [Từ điển đặc trưng và nguồn gốc dữ liệu](handbook-stage-2.md#từ-điển-đặc-trưng)

## Phân bố đặc trưng

Train có 863.006 giao dịch và validation có 287.364 giao dịch. P05, P50 và P95 tính trên các giá trị có mặt. Cột thiếu dùng tổng số dòng của tập làm mẫu số.

| Tập | Đặc trưng | P05 | P50 | P95 | Số dòng thiếu (%) |
| --- | --- | --- | --- | --- | --- |
| train | `log_amount` | 1.948763 | 3.821223 | 4.882423 | 0 (0.0000%) |
| train | `hour_sin` | -0.987688 | 0.000000 | 0.987688 | 0 (0.0000%) |
| train | `hour_cos` | -0.996195 | -0.584250 | 0.829038 | 0 (0.0000%) |
| train | `dow_sin` | -0.974928 | 0.000000 | 0.974928 | 0 (0.0000%) |
| train | `dow_cos` | -0.900969 | -0.222521 | 1.000000 | 0 (0.0000%) |
| train | `count_1h` | 0.000000 | 0.000000 | 1.000000 | 0 (0.0000%) |
| train | `count_24h` | 0.000000 | 2.000000 | 6.000000 | 0 (0.0000%) |
| train | `seconds_since_previous` | 1337.000000 | 21838.000000 | 144570.800000 | 4983 (0.5774%) |
| train | `amount_to_median_7d` | 0.254949 | 0.999626 | 1.973656 | 7047 (0.8166%) |
| train | `missing_history` | 0.000000 | 0.000000 | 0.000000 | 0 (0.0000%) |
| validation | `log_amount` | 1.945910 | 3.820346 | 4.883029 | 0 (0.0000%) |
| validation | `hour_sin` | -0.987688 | 0.000000 | 0.987688 | 0 (0.0000%) |
| validation | `hour_cos` | -0.996195 | -0.584250 | 0.831470 | 0 (0.0000%) |
| validation | `dow_sin` | -0.974928 | 0.000000 | 0.974928 | 0 (0.0000%) |
| validation | `dow_cos` | -0.900969 | -0.222521 | 1.000000 | 0 (0.0000%) |
| validation | `count_1h` | 0.000000 | 0.000000 | 1.000000 | 0 (0.0000%) |
| validation | `count_24h` | 0.000000 | 2.000000 | 6.000000 | 0 (0.0000%) |
| validation | `seconds_since_previous` | 1347.000000 | 22132.000000 | 147257.000000 | 3 (0.0010%) |
| validation | `amount_to_median_7d` | 0.256175 | 1.001033 | 1.970368 | 766 (0.2666%) |
| validation | `missing_history` | 0.000000 | 0.000000 | 0.000000 | 0 (0.0000%) |

Tỷ lệ giao dịch có `missing_history = 1` là 0.8166% trên train và 0.2666% trên validation.

## Đối chiếu ba giao dịch

Ba giao dịch được chọn trong ngày đầu validation để thấy cách đặc trưng dùng lịch sử train. Bảng dưới ghi kết quả tính trực tiếp từ số tiền và thời điểm của cùng khách hàng. Cả số giao dịch 24 giờ và tỷ lệ số tiền đều khớp với hàm A+B.

| Ca | Mã giao dịch | Khách hàng | Thời điểm | Số tiền | Số GD 7 ngày | Số GD 24 giờ | Trung vị 7 ngày | Số tiền / trung vị |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Lịch sử ngắn | `863216` | `11` | 2018-06-30 02:01:17 | 30.15 | 2 | 1 | 33.730 | 0.893863 |
| Lịch sử dài | `863677` | `2822` | 2018-06-30 04:16:03 | 97.28 | 21 | 8 | 105.560 | 0.921561 |
| Số tiền bất thường | `863087` | `3411` | 2018-06-30 00:57:50 | 106.55 | 12 | 0 | 15.235 | 6.993764 |

Đếm các dòng đánh dấu Có để tính số giao dịch trong `[t − 24 giờ, t)`. Lấy trung vị số tiền từ tất cả các dòng trong bảng lịch sử của từng ca rồi chia số tiền hiện tại cho trung vị. Các mã giao dịch và ngày giúp tra cột `TRANSACTION_ID` trong từng tệp gốc `data/YYYY-MM-DD.pkl`. [Ánh xạ cột Handbook](handbook-sample.md#ánh-xạ-cột)

### Lịch sử ngắn · `863216`

| Mã giao dịch | Thời điểm | Số tiền | Tập | Trong 24 giờ |
| --- | --- | --- | --- | --- |
| `825302` | 2018-06-26 04:20:22 | 44.08 | train | — |
| `858274` | 2018-06-29 12:03:57 | 23.38 | train | Có |

### Lịch sử dài · `863677`

| Mã giao dịch | Thời điểm | Số tiền | Tập | Trong 24 giờ |
| --- | --- | --- | --- | --- |
| `798991` | 2018-06-23 09:29:57 | 101.37 | train | — |
| `806413` | 2018-06-24 04:56:28 | 234.12 | train | — |
| `808249` | 2018-06-24 08:55:44 | 27.46 | train | — |
| `809229` | 2018-06-24 10:31:21 | 105.56 | train | — |
| `811427` | 2018-06-24 13:40:41 | 138.16 | train | — |
| `812115` | 2018-06-24 14:43:16 | 130.07 | train | — |
| `818929` | 2018-06-25 10:42:34 | 79.62 | train | — |
| `825101` | 2018-06-26 03:26:47 | 148.60 | train | — |
| `830941` | 2018-06-26 14:03:02 | 162.41 | train | — |
| `837674` | 2018-06-27 10:08:06 | 135.59 | train | — |
| `839883` | 2018-06-27 13:14:31 | 52.70 | train | — |
| `849042` | 2018-06-28 12:41:22 | 30.43 | train | — |
| `851382` | 2018-06-28 16:13:11 | 62.63 | train | — |
| `854228` | 2018-06-29 04:37:48 | 99.69 | train | Có |
| `855211` | 2018-06-29 07:14:32 | 176.66 | train | Có |
| `857564` | 2018-06-29 11:00:04 | 111.93 | train | Có |
| `857915` | 2018-06-29 11:31:20 | 110.01 | train | Có |
| `858248` | 2018-06-29 12:00:37 | 96.21 | train | Có |
| `861085` | 2018-06-29 16:25:42 | 18.24 | train | Có |
| `862295` | 2018-06-29 19:27:29 | 80.35 | train | Có |
| `863515` | 2018-06-30 03:36:46 | 162.33 | validation | Có |

### Số tiền bất thường · `863087`

| Mã giao dịch | Thời điểm | Số tiền | Tập | Trong 24 giờ |
| --- | --- | --- | --- | --- |
| `796563` | 2018-06-23 04:19:29 | 6.02 | train | — |
| `803441` | 2018-06-23 16:10:49 | 25.44 | train | — |
| `806127` | 2018-06-24 03:56:15 | 12.97 | train | — |
| `811887` | 2018-06-24 14:22:18 | 7.02 | train | — |
| `816749` | 2018-06-25 06:55:41 | 14.52 | train | — |
| `817485` | 2018-06-25 08:22:00 | 19.25 | train | — |
| `825163` | 2018-06-26 03:43:23 | 14.79 | train | — |
| `830686` | 2018-06-26 13:41:27 | 16.46 | train | — |
| `836122` | 2018-06-27 07:35:21 | 15.79 | train | — |
| `842910` | 2018-06-27 19:06:22 | 22.36 | train | — |
| `843072` | 2018-06-27 19:43:50 | 15.68 | train | — |
| `845723` | 2018-06-28 07:36:06 | 14.22 | train | — |

## Chạy lại

Chạy từ thư mục gốc repo sau khi cài thư viện trong `requirements.txt`.

```powershell
$handbookCheck = Join-Path $env:TEMP 'handbook-stage3-check.md'
python scripts/analyze_handbook_stage3.py $handbookCheck
```

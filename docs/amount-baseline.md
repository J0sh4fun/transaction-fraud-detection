# Xếp hạng cảnh báo theo số tiền

Mỗi bộ dữ liệu và ngày lịch trong `timestamp` có một danh sách riêng. Sắp `amount` giảm dần và chọn tối đa 50 giao dịch. Khi bằng số tiền, sắp `transaction_id` tăng dần theo giá trị số trên Handbook và theo thứ tự từ điển trên Sparkov. Hạng bắt đầu từ 1 mỗi ngày. Cột `label` được giữ để đối chiếu sau khi xếp hạng.

## Chạy lại

Chạy từ thư mục gốc bằng Python 3. Các lệnh dưới đây tạo lại hai CSV từ dữ liệu mẫu có sẵn.

```powershell
python scripts/rank_amount_baseline.py data/samples/handbook_2018-04-01.csv data/samples/alerts_handbook_2018-04-01.csv
python scripts/rank_amount_baseline.py data/samples/sparkov_2019-01-02.csv data/samples/alerts_sparkov_2019-01-02.csv
```

## Kết quả kiểm tra

| Nguồn | Ngày | Số giao dịch | Số cảnh báo | Số nhãn `1` trong cảnh báo | Đầu ra |
|---|---|---:|---:|---:|---|
| Handbook | 2018-04-01 | 9.488 | 50 | 3 | [CSV cảnh báo Handbook](../data/samples/alerts_handbook_2018-04-01.csv) |
| Sparkov | 2019-01-02 | 1.118 | 50 | 5 | [CSV cảnh báo Sparkov](../data/samples/alerts_sparkov_2019-01-02.csv) |

Dữ liệu thử gồm một ngày có 53 giao dịch Handbook, trong đó 52 giao dịch cùng số tiền và có điểm hòa ở hạng 50. Chương trình giữ đúng 50 dòng, xếp mã `57` hạng 50 và bỏ mã `58`. Ngày Handbook tiếp theo có một giao dịch và Sparkov có hai giao dịch trong ngày đầu. Hai nhóm nhỏ giữ đủ số dòng và bắt đầu lại từ hạng 1. Đảo thứ tự đầu vào cho cùng kết quả.

Đã kiểm tra độc lập thứ tự của 50 mã giao dịch trong mỗi CSV, đối chiếu số tiền và nhãn với tệp mẫu theo từng mã, và chạy hai lần để xác nhận nội dung CSV giống nhau.

| Nguồn | Hạng | Mã giao dịch | Số tiền | Nhãn | Cột trong dữ liệu gốc |
|---|---:|---|---:|---:|---|
| Handbook | 1 | `6549` | 226.40 | 1 | `TRANSACTION_ID` |
| Sparkov | 2 | `248c2746e78f2ec713df51254ff1b302` | 844.8 | 1 | `trans_num` |

Hai mã trên đã được đối chiếu trong CSV mẫu. Để truy về dữ liệu gốc, dùng các cột trong bảng cùng hướng dẫn lấy nguồn tại [Handbook](handbook-sample.md) và [Sparkov](sparkov-sample.md). TV3 duyệt mục 1.4 theo [bảng tiến độ](progress.md).

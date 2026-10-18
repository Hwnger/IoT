# IoT Environmental Monitoring System

Hệ thống giám sát môi trường sử dụng ESP32 mô phỏng trên Wokwi, giao thức MQTT, InfluxDB và Streamlit. Dự án thu thập dữ liệu nhiệt độ, độ ẩm, lưu trữ dữ liệu theo thời gian, tiền xử lý và trực quan hóa kết quả.

## 1. Mục tiêu dự án

- Mô phỏng thiết bị nhúng ESP32 và cảm biến DHT22 trên Wokwi.
- Truyền dữ liệu cảm biến qua MQTT broker.
- Sử dụng Python để nhận, kiểm tra và lưu dữ liệu.
- Lưu trữ dữ liệu gốc và dữ liệu đã xử lý bằng InfluxDB.
- Tiền xử lý dữ liệu nhằm phát hiện giá trị bất thường, xử lý dữ liệu thiếu và tính toán các đặc trưng theo thời gian.
- Xây dựng dashboard bằng Streamlit để theo dõi dữ liệu và thống kê.

## 2. Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Thiết bị nhúng mô phỏng | ESP32, Wokwi |
| Cảm biến | DHT22 |
| Ngôn ngữ nhúng | Arduino/C++ |
| Truyền dữ liệu | MQTT |
| MQTT broker | HiveMQ Public Broker hoặc broker được cấu hình |
| Xử lý dữ liệu | Python, Pandas, NumPy |
| Cơ sở dữ liệu chuỗi thời gian | InfluxDB 2.x |
| Trực quan hóa | Streamlit, Plotly |
| Quản lý mã nguồn | Git, GitHub |

## 3. Kiến trúc hệ thống

```text
ESP32 + DHT22 (Wokwi)
          |
          | MQTT Publish
          v
    MQTT Broker
          |
          | MQTT Subscribe
          v
 Python Subscriber
          |
          v
       InfluxDB
          |
          v
   Data Preprocessing
          |
          v
  Streamlit Dashboard
```

## 4. Cấu trúc thư mục

```text
iot-monitoring/
├── wokwi/
│   ├── sketch.ino
│   ├── libraries.txt
│   └── diagram.json
├── src/
│   ├── subscriber.py
│   ├── preprocess.py
│   └── dashboard.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 5. Yêu cầu môi trường

- Python 3.10 trở lên, hoặc phiên bản tương thích với các thư viện sử dụng.
- Wokwi để chạy mô phỏng ESP32.
- MQTT broker có thể truy cập từ Wokwi và máy tính.
- InfluxDB 2.x đang hoạt động.
- Git để quản lý mã nguồn.

## 6. Cài đặt

### Bước 1. Tải dự án

```bash
git clone <GITHUB_REPOSITORY_URL>
cd iot-monitoring
```

### Bước 2. Tạo môi trường Python

Trên Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Cài đặt thư viện:

```bash
pip install -r requirements.txt
```

### Bước 3. Cấu hình môi trường

Tạo file `.env` ở thư mục gốc dựa trên `.env.example`. Điền thông tin InfluxDB và MQTT phù hợp với chương trình.

Ví dụ các biến cấu hình:

```dotenv
MQTT_BROKER=broker.hivemq.com
MQTT_PORT=1883
MQTT_TOPIC=<YOUR_UNIQUE_TOPIC>

INFLUX_URL=http://localhost:8086
INFLUX_ORG=iot_lab
INFLUX_BUCKET=iot_data
INFLUX_TOKEN=<YOUR_INFLUXDB_TOKEN>
```

Các biến trên là ví dụ. Mã nguồn phải được viết để đọc đúng tên biến đã cấu hình. Không commit file `.env` hoặc token thật lên GitHub.

### Bước 4. Khởi động InfluxDB

Khởi động InfluxDB 2.x và kiểm tra khả năng truy cập. Tạo hoặc xác nhận tổ chức, bucket và token có quyền ghi dữ liệu phù hợp.

### Bước 5. Chạy ESP32 trên Wokwi

1. Mở dự án Wokwi.
2. Kiểm tra cấu hình Wi-Fi, MQTT broker và topic.
3. Khởi động mô phỏng.
4. Kiểm tra Serial Monitor để xác nhận ESP32 kết nối MQTT và gửi bản tin.

### Bước 6. Chạy Python Subscriber

Mở terminal tại thư mục dự án và chạy:

```bash
python src/subscriber.py
```

Kiểm tra bản tin nhận được. Nếu chương trình được đặt ở vị trí khác, điều chỉnh đường dẫn tương ứng.

### Bước 7. Tiền xử lý dữ liệu

Sau khi có dữ liệu trong InfluxDB, chạy:

```bash
python src/preprocess.py
```

Chương trình tiền xử lý có thể thực hiện các bước như phát hiện ngoại lệ bằng IQR hoặc Z-score, lấy mẫu lại theo thời gian, xử lý một số khoảng thiếu ngắn, tính trung bình trượt và chuẩn hóa dữ liệu.

Kết quả thực tế phụ thuộc vào cách triển khai trong mã nguồn và cấu hình thời gian truy vấn.

### Bước 8. Khởi động dashboard

```bash
streamlit run src/dashboard.py
```

Mở địa chỉ local do Streamlit hiển thị trong terminal để xem dashboard.

## 7. Cơ sở dữ liệu

Các measurement dự kiến trong InfluxDB:

| Measurement | Mục đích |
|---|---|
| `environment` | Dữ liệu cảm biến gốc |
| `environment_processed` | Dữ liệu sau tiền xử lý |
| `benchmark` | Dữ liệu đo hiệu năng, nếu đã triển khai |

Schema và tên field thực tế cần được đối chiếu với mã ghi dữ liệu. Không phải mọi measurement đều bắt buộc phải có trong mọi phiên bản của dự án.

## 8. Thực nghiệm và đánh giá

Các chỉ số có thể dùng để đánh giá hệ thống:

- Số bản tin được gửi và số bản tin nhận được.
- Tỷ lệ mất bản tin.
- Độ trễ truyền tin và thời gian xử lý, nếu có cơ chế đo phù hợp.
- Số lượng giá trị bất thường trước và sau xử lý.
- Số điểm dữ liệu được lưu trữ.
- Dung lượng dữ liệu và khả năng cập nhật dashboard.

Kết quả đo:

| Chỉ số | Kết quả |
|---|---|
| Tổng số bản tin gửi | 900 |
| Tổng số bản tin nhận | 895 |
| Tỷ lệ mất bản tin | 5/0.55% |
| Độ trễ trung bình | 24.5 ms |


## 9. Hình ảnh minh họa

Bổ sung ảnh chụp thực tế vào `docs/screenshots/`, ví dụ:

- Sơ đồ mạch ESP32 và DHT22 trên Wokwi.
- Serial Monitor của ESP32.
- Python Subscriber nhận bản tin MQTT.
- Dữ liệu trong InfluxDB.
- Dashboard Streamlit.
- Kết quả thực nghiệm.

Ví dụ nhúng ảnh:

```markdown
![Wokwi simulation](docs/screenshots/wokwi.png)
```

## 10. Hạn chế

- Wokwi là môi trường mô phỏng, không phản ánh đầy đủ hiệu năng của phần cứng vật lý.
- MQTT broker công khai có thể có độ trễ, gián đoạn hoặc giới hạn tài nguyên.
- Dữ liệu đo được phụ thuộc vào môi trường chạy và thời gian thử nghiệm.
- Cơ chế xử lý mất bản tin, kết nối lại và bảo mật cần được cải thiện nếu triển khai thực tế.

## 11. Hướng phát triển

- Sử dụng MQTT có xác thực và TLS.
- Bổ sung cơ chế reconnect và ghi log lỗi.
- Hoàn thiện cơ chế phát hiện bản tin thiếu, trùng lặp và sai thứ tự.
- Đánh giá hiệu năng qua nhiều lần chạy thử nghiệm.
- Mở rộng hệ thống với thiết bị vật lý và cảm biến thực tế.

## 12. Tác giả

- Sinh viên: Nguyễn Duy Hưng
- Lớp: Nhóm 5
- Học phần: IoT và ứng dụng
- Giảng viên hướng dẫn: Nguyễn Tài Tuyên
# IoT

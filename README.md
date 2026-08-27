# 🚀 QR Code API Server (Windows Standalone)

Hệ thống cung cấp dịch vụ máy chủ Đọc và Tạo Mã QR tốc độ cao, hỗ trợ chạy nền trên Windows với giao diện tinh chỉnh chuyên nghiệp. 
Đặc biệt, hệ thống sử dụng thuật toán AI WeChatQR cho khả năng quét mã cực nhạy kể cả khi mã bị mờ, hỏng hoặc ở góc nghiêng.

---

## ✨ Tính Năng Nổi Bật Mới Nhất

- **Giao Diện Quản Lý Thông Minh:** Bật/Tắt Server linh hoạt bằng một nút bấm mà không cần khởi động lại ứng dụng.
- **Tự Động Nhận Diện IP:** Tự động phát hiện và gợi ý địa chỉ IP LAN để bạn dễ dàng quét bằng điện thoại. Hỗ trợ nút sao chép nhanh (Copy URL).
- **Chạy Ngầm (System Tray):** Tính năng ẩn cửa sổ xuống khay hệ thống, không gây vướng víu màn hình.
- **Tùy Biến Cấu Hình (config.json):** Tự động lưu cấu hình mạng và giới hạn dung lượng ảnh mà không cần can thiệp mã nguồn. Tùy chọn Bật/Tắt trang tài liệu API (`/docs`).
- **Đóng Gói Độc Lập:** Dễ dàng build thành file `.exe` bằng PyInstaller `--onedir`, tách biệt thư viện và file thực thi giúp khởi chạy siêu tốc.
- **Hỗ Trợ Gọi Nội Bộ (Embedded):** Tách biệt lõi quét mã (`QREngine`) giúp bạn dễ dàng nhúng vào ứng dụng Python khác mà không cần bật Server HTTP.

---

## 🚀 Hướng Dẫn Sử Dụng (Dành Cho Người Dùng)

### Cách 1: Chạy trực tiếp từ mã nguồn
1. Chạy file **`run.bat`**. (Script sẽ tự động tạo môi trường ảo và cài đặt thư viện nếu chưa có).
2. Giao diện phần mềm sẽ hiện lên. Bạn có thể cấu hình Host, Port và nhấn **Khởi Chạy Server**.
3. (Tùy chọn) Nhấn **Ẩn xuống khay** để phần mềm chạy ngầm dưới taskbar Windows.

### Cách 2: Đóng gói thành phần mềm độc lập (.exe)
Nếu bạn muốn gửi cho người khác sử dụng mà không cần cài Python:
1. Chạy file **`build_exe.bat`**.
2. Đợi quá trình Build hoàn tất.
3. Phần mềm của bạn sẽ nằm gọn trong thư mục `dist/QR_API_Server`. Chỉ cần nén thư mục này lại là có thể mang đi mọi nơi!

---

## 💻 Nhúng API Nội Bộ (Dành Cho Lập Trình Viên)

Bạn không nhất thiết phải chạy HTTP Server. Lõi `QREngine` được thiết kế hoàn toàn độc lập, cho phép bạn nhúng trực tiếp vào các dự án Python khác (Bot Telegram, Crawler, Data Pipeline...) với tốc độ quét **nhanh hơn nhiều lần**.

### Ví dụ Nhúng (Embedded Usage)

Chỉ cần copy thư mục `app` (chứa lõi code và model) vào dự án của bạn:

```python
import asyncio
from app.engine import QREngine

# 1. Khởi tạo Engine quét mã (Chỉ chạy 1 lần lúc bật app để nạp AI vào RAM)
engine = QREngine(model_dir="app/models")

# 2. Đọc file ảnh dưới dạng Bytes (hoặc lấy từ OpenCV/Camera)
with open("test.jpg", "rb") as f:
    image_bytes = f.read()

# --- CÁCH 1: Dành cho code Đồng bộ bình thường (Sync) ---
ket_qua = engine._sync_opencv_decode(image_bytes)
if ket_qua and ket_qua["status"] == "success":
    print("Nội dung QR:", ket_qua["data"])

# --- CÁCH 2: Dành cho code Bất đồng bộ (Asyncio/FastAPI) ---
async def main():
    ket_qua = await engine.decode(image_bytes)
    print(ket_qua)

# asyncio.run(main())
```

---

## 📡 HTTP API Endpoints (Khi Chạy Server)

Nếu bạn chạy Server, bạn có thể tương tác với các HTTP API qua mọi ngôn ngữ lập trình.

### 1. Quét Mã QR (Scan)
- **Method:** `POST /scan`
- **Body:** `multipart/form-data` chứa tham số `file` (File ảnh).
- **Phản hồi:** Trả về nội dung *Text thuần túy (Plain Text)* của mã QR (Đúng như định dạng gốc). Lỗi sẽ trả về HTTP 400.

### 2. Tạo Mã QR (Generate)
- **Method:** `GET /generate`
- **Params:** `content` (Nội dung), `size` (Kích thước ô), `border` (Viền).
- **Phản hồi:** File ảnh định dạng PNG.

# QR API Server 2.0

Một máy chủ API độc lập chuyên dụng cho việc nhận diện, quét mã QR (đặc biệt tối ưu cho mã QR trên thẻ CCCD) và tạo mã QR tùy chỉnh. Phiên bản 2.0 đi kèm với một **Windows Desktop App** hoàn chỉnh, cho phép quản lý máy chủ, cấu hình cổng (port) và bảo mật bằng API Key qua giao diện đồ họa.

## 🌟 Tính năng nổi bật

- **Giải mã đa lớp (Multi-layer QR Engine):** Kết hợp WeChat AI (Caffe model), OpenCV QRCodeDetector và pyzbar để đảm bảo khả năng quét mã QR CCCD bị mờ, lóa hoặc chụp ở góc nghiêng.
- **Tạo mã QR tùy chỉnh:** Khả năng tạo mã QR với tùy chỉnh kích thước, màu sắc và mức độ sửa lỗi (Error Correction). Hỗ trợ tải xuống ảnh PNG chất lượng cao.
- **Windows Desktop App:** Giao diện điều khiển (Tkinter) với Dark Theme, hỗ trợ ẩn xuống khay hệ thống (System Tray).
- **Bảo mật API Key:** Tính năng bật/tắt yêu cầu mã xác thực (`X-API-Key`) cho mọi request, đảm bảo máy chủ không bị truy cập trái phép.
- **Giao diện Web tích hợp:** Trang tĩnh được phục vụ trực tiếp qua máy chủ, cung cấp công cụ quét và tạo mã trực quan trên trình duyệt.
- **Đóng gói thành một file `.exe` duy nhất:** Dễ dàng phân phối với kịch bản build PyInstaller đi kèm.

---

## 📁 Cấu trúc thư mục

```text
QR_API_Server/
├── app.py                # Ứng dụng Desktop (Windows GUI) quản lý server
├── server.py             # Lõi máy chủ FastAPI (Routes, Middleware)
├── qr_engine.py          # Động cơ giải mã QR (WeChat AI, OpenCV, pyzbar)
├── config.py             # Quản lý cấu hình (config.json) & tạo API Key
├── build.ps1             # Script đóng gói toàn bộ dự án thành file .exe (PyInstaller)
├── setup.ps1             # Script cài đặt môi trường ảo (.venv) và tải Models AI
├── run.ps1               # Script chạy ứng dụng qua cmd/powershell
├── requirements.txt      # Danh sách thư viện Python
├── models/               # (Sẽ được tải về) Chứa file mô hình WeChat QR AI Caffe
└── static/               # Thư mục web UI
    ├── index.html        # Trang chủ & Hướng dẫn API
    ├── scan.html         # Công cụ quét QR
    └── generate.html     # Công cụ tạo QR
```

---

## 🚀 Hướng dẫn sử dụng (Chạy từ mã nguồn)

### 1. Cài đặt môi trường
Bật PowerShell ở quyền quản trị (nếu cần) và chạy kịch bản thiết lập để tạo `Virtual Environment` và tự động tải các models AI:
```powershell
.\setup.ps1
```

### 2. Khởi động phần mềm
Khởi chạy Windows Desktop App bằng script:
```powershell
.\run.ps1
```
*Hoặc chạy trực tiếp qua Python:*
```powershell
.\.venv\Scripts\python.exe app.py
```

### 3. Sử dụng App Quản Lý
- **Điều khiển:** Nhấn nút **Khởi Động** hoặc **Dừng** để bật/tắt máy chủ FastAPI.
- **Cấu hình:** Đổi Port hoặc Host trong tab **Cấu Hình Server**. Bấm `Áp dụng & Khởi động lại`.
- **Bảo mật:** Check vào ô `Bật xác thực API Key`, lưu lại và khởi động lại server. Mã bảo mật sẽ được tạo ngẫu nhiên.
- **Khay hệ thống:** Khi đóng cửa sổ, ứng dụng sẽ thu nhỏ xuống khay hệ thống góc phải màn hình.

---

## 📦 Hướng dẫn đóng gói (Build `.exe`)

Sử dụng kịch bản `build.ps1` để biên dịch toàn bộ dự án (bao gồm cả môi trường ảo, models và giao diện) thành một file `.exe` duy nhất có thể mang sang máy tính khác mà không cần cài Python.

```powershell
.\build.ps1
```
- Kết quả sẽ được lưu ở: `dist\QRAPIServer\QRAPIServer.exe`.
- Khi mang sang máy khác, chỉ cần copy nguyên thư mục `dist\QRAPIServer\`.

---

## 🔌 API Endpoints

Nếu API Key được kích hoạt, bạn cần truyền mã này vào Header (`X-API-Key`) hoặc Query Param (`?api_key=...`). Xem tài liệu chi tiết hơn tại `http://localhost:<port>/` (Trang chủ của máy chủ sau khi bật).

### 1. Quét mã QR (`POST /api/scan-qr`)
- **Body:** `multipart/form-data` chứa trường `file` (ảnh định dạng JPG/PNG).
- **Kết quả trả về:** Dữ liệu text giải mã được (hoặc phân tách trường nếu là thẻ CCCD Việt Nam).

### 2. Tạo mã QR (`GET /api/generate-qr`)
- **Query Params:** `data` (Nội dung), `size` (Kích thước px), `error_correction` (L, M, Q, H), `fg` (Màu QR), `bg` (Màu nền).
- **Kết quả trả về:** Ảnh PNG dạng stream.

### 3. Kiểm tra trạng thái (`GET /health`)
- Trả về JSON chứa trạng thái server và tình trạng sẵn sàng của các động cơ giải mã.

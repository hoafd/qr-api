# Máy Chủ QR Code 🚀

Hệ thống siêu tốc cung cấp dịch vụ máy chủ Đọc và Tạo Mã QR, triển khai nhanh và xử lý hoàn toàn Offline. Tích hợp sẵn bộ máy giải mã siêu việt WeChatQR kết hợp với thư viện xử lý ảnh OpenCV.

---

## ✨ Tính Năng Nổi Bật

- **Trải Nghiệm WebApp Trực Tiếp:** Không cần phần mềm bên thứ 3. Một Giao diện Single Page Application (SPA) trực quan cài cắm thẳng ở máy chủ cho phép người dùng thao tác "kéo-thả" ảnh và xuất thông tin ngay lập tức.
- **API Dành Cho Lập Trình Viên:** Hỗ trợ giao thức phi trạng thái (RESTful) với chuẩn POST (Giải Web) / GET (Lấy Ảnh). Bắn lệnh từ thư viện nào cũng chạy.
- **Bảo Mật 100% Offline (Air-gapped Ready):** Xử lý hình ảnh tốn GPU/CPU cực nặng nhưng diễn ra hoàn toàn nội bộ trong RAM của bạn, không gửi yêu cầu API bên ngoài hay cầu viện nhờ vả Google AI. Tuyệt đối an toàn dữ liệu nhạy cảm.
- **Tiếng Việt Ưu Tiên:** UX/UI chuẩn hoá ngôn ngữ địa phương.
- **Tối Ưu Chống Tấn Công (Anti-DoS):** Khoá trần nạp liệu file (<10MB) và giới hạn tham số sinh ma trận khắt khe để bảo vệ máy chủ tuyệt đối.

## 📦 Kiến Trúc Công Nghệ

- **Web Server:** FastAPI & Uvicorn (Tối đa hoá I/O bất đồng bộ).
- **Core Xử lý Ảnh:** OpenCV (`opencv-contrib-python-headless`), mảng `Numpy`, `Pillow`.
- **Lõi Giải Mã (Engine):** WeChatQR Model (.caffemodel + .prototxt).
- **Hạ Tầng:** Tự động hoá qua Docker & Docker Compose.
- **Frontend:** Vanilla JS & CSS Glassmorphism siêu mượt.

---

## 🚀 Khởi Động Nhanh Từ Con Số 0

Bạn chỉ cần một máy chủ Linux mộc mạc chưa cần cài cắm gì. Dưới đây là toàn bộ quy trình:

### 1. Tải Mã Nguồn Về Máy (Git Clone)
Mở cửa sổ dòng lệnh Terminal lên và gõ:
```bash
git clone -b linux https://github.com/hoafd/qr-api.git
cd qr-api
```

### 2. Cài Đặt Siêu Tốc Docker (Nếu máy chưa có)
Chạy trực tiếp 1 dòng lệnh này để hệ thống tải và cắm thẳng Docker Engine vào nhân Linux:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
```

### 3. Đóng Gói Và Đẩy Server Lên Trực Tuyến
Từ chính thư mục dự án vừa clone về, bạn đánh thức máy chủ bằng lệnh:
```bash
sudo docker compose up --build -d
```
Lệnh trên thực hiện một chu trình khép kín: Khởi tạo mô trường Python 3.11 siêu nhỏ gọn ➔ Cài thư viện ➔ Nhồi lõi Code ➔ Kích hoạt Cổng mạng 8000.

---

## 🎯 Hướng Dẫn Sử Dụng

### Giao Diện Người Dùng (UI)
Sau vài chục giây cho lần build đầu tiên, bạn hãy mở trình duyệt và trỏ vào địa chỉ IP của máy chủ:
👉 `http://[IP-MÁY]:8000/` (Hoặc `http://localhost:8000/` nếu chạy trên cùng thiết bị).

Khung không gian trải nghiệm chia làm 2 thẻ Tab cực kỳ dễ hiểu:
- **Đọc Mã:** Bốc một cái ảnh QR ném vào là máy chữ lại ngay chữ cất trong đó.
- **Tạo Mã:** Ném vào một câu chữ, lấy ngay 1 bức ảnh ma trận ra.

### 📡 Tương Tác Bằng API Dành Cho Lập Trình Viên

Với những nhà phát triển App Mobile hoặc phần mềm máy tính, bạn đưa hệ thống QR này đóng vai làm 1 node vệ tinh theo đúng API đặc tả sau:

#### 1. API Quét Mã (POST `/scan`)
- **Giao thức:** Nhét một form-data có chứa khoá `file`. File này mang thân thể của hình ảnh (`.png`, `.jpeg`).
- **Phản hồi:** Trả thắng về mã thuần `Text/Plain` nồng độ cao (Ví dụ: `https://...`). Nếu có lỗi từ ảnh mờ/hỏng, trả về chuỗi bắt đầu bằng cụm từ `ERROR: `.

#### 2. API Dịch Sinh Tự Mã (GET `/generate`)
- **Giao thức:** Tương tác trên URL: `http://[IP-MÁY]:8000/generate?content=Nội_dung_của_bạn`. 
- **Các biến hỗ trợ (Tùy chọn):** 
  - `size` (Kích cỡ ô ảnh nhỏ, mặc định: 10, max: 40)
  - `border` (Dày viền, mặc định: 4, max: 10).
- **Phản hồi:** Trả trực diện về nhị phân `image/png`.

---

## Lời Cảm Ơn
Mã nguồn được cấu trúc và tối ưu hoá đạt tiêu chuẩn Microservice. Giữ cho máy móc của bạn được cách ly 100% nhưng vẫn sở hữu sức mạnh xử lý QR công nghiệp hàng đầu thế giới!

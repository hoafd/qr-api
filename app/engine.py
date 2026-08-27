import cv2
import numpy as np
import os
import logging
import asyncio
import qrcode
from io import BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QREngine")

class QREngine:
    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self.detector = None

        # Init WeChatQR
        try:
            d_p = os.path.join(self.model_dir, "detect.prototxt")
            d_c = os.path.join(self.model_dir, "detect.caffemodel")
            s_p = os.path.join(self.model_dir, "sr.prototxt")
            s_c = os.path.join(self.model_dir, "sr.caffemodel")
            if os.path.exists(d_p) and os.path.exists(d_c):
                self.detector = cv2.wechat_qrcode_WeChatQRCode(d_p, d_c, s_p, s_c)
                logger.info("Engine: WeChat QR loaded.")
        except Exception as e:
            logger.error(f"WeChat Init Error: {e}")

    # Chức năng tạo QR (Chạy rất nhanh nên không lo block event loop)
    def generate_qr(self, content: str, box_size: int = 10, border: int = 4):
        qr = qrcode.QRCode(version=1, box_size=box_size, border=border)
        qr.add_data(content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        return img_buffer

    # [MỚI] Tách riêng phần xử lý ảnh OpenCV thành hàm đồng bộ (CPU-bound)
    def _sync_opencv_decode(self, image_bytes):
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: 
            return {"status": "error", "message": "Invalid image"}

        if self.detector:
            try:
                res, _ = self.detector.detectAndDecode(img)
                if res and res[0]: 
                    return {"status": "success", "data": res[0], "method": "wechat"}
            except Exception:
                pass

        # 2. OpenCV Basic
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            detector_basic = cv2.QRCodeDetector()
            val, _, _ = detector_basic.detectAndDecode(gray)
            if val: 
                return {"status": "success", "data": val, "method": "opencv_basic"}
        except Exception:
            pass

        return None # Trả về None nếu OpenCV không đọc được

    async def decode(self, image_bytes):
        # 1 & 2. Đẩy toàn bộ quá trình đọc ảnh và OpenCV sang Threadpool
        # Event Loop của FastAPI lúc này hoàn toàn rảnh tay để nhận request khác
        cv2_result = await asyncio.to_thread(self._sync_opencv_decode, image_bytes)
        
        # Nếu OpenCV hoặc WeChatQR đã quét thành công (hoặc lỗi ảnh hỏng), trả về luôn
        if cv2_result:
            if cv2_result.get("status") == "error":
                return cv2_result
            return cv2_result

        return {"status": "failed", "message": "No QR found"}

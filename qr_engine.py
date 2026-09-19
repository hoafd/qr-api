import cv2
import numpy as np
import logging
import asyncio
import os
import requests
import sys

logger = logging.getLogger("QRServer.Engine")


class QREngine:
    """
    QR Decode Engine đa tầng:
      Layer 1 — WeChat QR AI (Caffe model, mạnh nhất, chống mờ/chói)
      Layer 2 — OpenCV Standard QRCodeDetector
      Layer 3 — pyzbar (fallback cuối)

    Mỗi layer áp dụng preprocessing pipeline trước khi decode:
      - Original image
      - Grayscale
      - CLAHE (Contrast Limited Adaptive Histogram Equalization)
      - Adaptive Threshold
      - Upscale x2 (cho ảnh nhỏ, mờ)
    """

    def __init__(self):
        self.detector_basic = cv2.QRCodeDetector()
        self.detector_wechat = None
        self._pyzbar_decode = None

        # Đường dẫn model — hỗ trợ cả PyInstaller bundle và dev mode
        if hasattr(sys, "_MEIPASS"):
            self.model_dir = os.path.join(sys._MEIPASS, "models")
        else:
            self.model_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "models"
            )

        os.makedirs(self.model_dir, exist_ok=True)

        self._init_wechat()
        self._init_pyzbar()

    # ------------------------------------------------------------------
    # Khởi tạo các engine
    # ------------------------------------------------------------------

    def _init_wechat(self):
        """Khởi tạo WeChat QR AI engine từ Caffe models."""
        model_files = [
            "detect.prototxt",
            "detect.caffemodel",
            "sr.prototxt",
            "sr.caffemodel",
        ]
        model_urls = {
            "detect.prototxt": "https://raw.githubusercontent.com/WeChatCV/opencv_3rdparty/wechat_qrcode/detect.prototxt",
            "detect.caffemodel": "https://raw.githubusercontent.com/WeChatCV/opencv_3rdparty/wechat_qrcode/detect.caffemodel",
            "sr.prototxt": "https://raw.githubusercontent.com/WeChatCV/opencv_3rdparty/wechat_qrcode/sr.prototxt",
            "sr.caffemodel": "https://raw.githubusercontent.com/WeChatCV/opencv_3rdparty/wechat_qrcode/sr.caffemodel",
        }

        all_exist = all(
            os.path.exists(os.path.join(self.model_dir, name)) for name in model_files
        )

        if all_exist:
            # Ưu tiên load local — KHÔNG cần mạng
            try:
                self.detector_wechat = cv2.wechat_qrcode_WeChatQRCode(
                    os.path.join(self.model_dir, "detect.prototxt"),
                    os.path.join(self.model_dir, "detect.caffemodel"),
                    os.path.join(self.model_dir, "sr.prototxt"),
                    os.path.join(self.model_dir, "sr.caffemodel"),
                )
                logger.info("Engine: WeChat QR AI loaded from local models.")
            except Exception as e:
                logger.error(f"Engine: WeChat init error (local): {e}")
            return

        # Thiếu model → thử download
        logger.info("Engine: WeChat models not found. Attempting download...")
        try:
            downloaded_all = True
            for name, url in model_urls.items():
                target = os.path.join(self.model_dir, name)
                if not os.path.exists(target):
                    logger.info(f"  Downloading: {name} ...")
                    r = requests.get(url, timeout=30)
                    if r.status_code == 200:
                        with open(target, "wb") as f:
                            f.write(r.content)
                        logger.info(f"  ✓ {name} saved ({len(r.content)//1024} KB)")
                    else:
                        logger.warning(f"  ✗ Failed to download {name}: HTTP {r.status_code}")
                        downloaded_all = False

            if downloaded_all:
                self.detector_wechat = cv2.wechat_qrcode_WeChatQRCode(
                    os.path.join(self.model_dir, "detect.prototxt"),
                    os.path.join(self.model_dir, "detect.caffemodel"),
                    os.path.join(self.model_dir, "sr.prototxt"),
                    os.path.join(self.model_dir, "sr.caffemodel"),
                )
                logger.info("Engine: WeChat QR AI loaded after download.")
            else:
                logger.warning("Engine: Some WeChat models missing. WeChat layer disabled.")
        except Exception as e:
            logger.error(f"Engine: WeChat init failed: {e}")

    def _init_pyzbar(self):
        """Khởi tạo pyzbar làm engine fallback thứ 3."""
        try:
            from pyzbar.pyzbar import decode as pyzbar_decode
            self._pyzbar_decode = pyzbar_decode
            logger.info("Engine: pyzbar loaded successfully.")
        except ImportError:
            logger.warning("Engine: pyzbar not available. Layer 3 disabled.")

    # ------------------------------------------------------------------
    # Preprocessing pipeline
    # ------------------------------------------------------------------

    def _get_variants(self, img: np.ndarray) -> list[tuple[str, np.ndarray]]:
        """
        Tạo danh sách các biến thể ảnh để thử decode lần lượt.
        Thứ tự: original → gray → CLAHE → adaptive threshold → upscale
        """
        variants: list[tuple[str, np.ndarray]] = []

        # 1. Original (BGR)
        variants.append(("original", img))

        # 2. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        variants.append(("gray", gray))

        # 3. CLAHE — cải thiện độ tương phản cục bộ (chống chói/tối)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray_clahe = clahe.apply(gray)
        variants.append(("clahe", gray_clahe))

        # 4. Adaptive Threshold — tách QR khỏi nền không đồng đều
        adaptive = cv2.adaptiveThreshold(
            gray_clahe, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        variants.append(("adaptive_threshold", adaptive))

        # 5. Upscale x2 — giúp đọc QR nhỏ hoặc mờ
        h, w = img.shape[:2]
        if max(h, w) < 800:
            upscaled = cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
            variants.append(("upscale_2x", upscaled))
            gray_up = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
            clahe_up = clahe.apply(gray_up)
            variants.append(("upscale_2x_clahe", clahe_up))

        return variants

    # ------------------------------------------------------------------
    # Decode logic
    # ------------------------------------------------------------------

    def _try_wechat(self, img: np.ndarray) -> str | None:
        """Thử decode bằng WeChat QR AI. Trả về chuỗi nếu thành công."""
        if not self.detector_wechat:
            return None
        try:
            # WeChat nhận BGR
            src = img if len(img.shape) == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            res, _ = self.detector_wechat.detectAndDecode(src)
            if res and res[0]:
                return res[0]
        except Exception as e:
            logger.debug(f"WeChat decode error: {e}")
        return None

    def _try_opencv(self, img: np.ndarray) -> str | None:
        """Thử decode bằng OpenCV standard detector."""
        try:
            val, _, _ = self.detector_basic.detectAndDecode(img)
            if val:
                return val
        except Exception as e:
            logger.debug(f"OpenCV decode error: {e}")
        return None

    def _try_pyzbar(self, img: np.ndarray) -> str | None:
        """Thử decode bằng pyzbar."""
        if not self._pyzbar_decode:
            return None
        try:
            # pyzbar cần grayscale hoặc RGB
            src = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            results = self._pyzbar_decode(src)
            if results:
                return results[0].data.decode("utf-8", errors="replace")
        except Exception as e:
            logger.debug(f"pyzbar decode error: {e}")
        return None

    def _sync_decode(self, image_bytes: bytes) -> dict:
        """
        Decode QR từ image bytes. Chạy sync — gọi qua asyncio.to_thread().

        Returns:
            {status: "success"|"failed"|"error", data?: str, method?: str, message?: str}
        """
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return {"status": "error", "message": "Không đọc được ảnh (định dạng không hợp lệ)"}

            variants = self._get_variants(img)

            # Layer 1: WeChat QR AI (áp dụng cho tất cả biến thể)
            for name, variant in variants:
                result = self._try_wechat(variant)
                if result:
                    logger.info(f"Decoded via wechat_ai [{name}]")
                    return {"status": "success", "data": result, "method": f"wechat_ai/{name}"}

            # Layer 2: OpenCV standard
            for name, variant in variants:
                result = self._try_opencv(variant)
                if result:
                    logger.info(f"Decoded via opencv [{name}]")
                    return {"status": "success", "data": result, "method": f"opencv/{name}"}

            # Layer 3: pyzbar
            for name, variant in variants:
                result = self._try_pyzbar(variant)
                if result:
                    logger.info(f"Decoded via pyzbar [{name}]")
                    return {"status": "success", "data": result, "method": f"pyzbar/{name}"}

            logger.info("All decode layers failed.")
            return {"status": "failed", "message": "Không nhận diện được mã QR sau khi thử tất cả engine"}

        except Exception as e:
            logger.error(f"QR Decoding critical error: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def decode(self, image_bytes: bytes) -> dict:
        """Async wrapper — không block event loop."""
        return await asyncio.to_thread(self._sync_decode, image_bytes)

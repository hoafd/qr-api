"""
QR API Server — FastAPI Standalone
=====================================
Endpoints:
  GET  /              — Trang chủ (HTML)
  GET  /scan          — Trang quét QR (HTML)
  GET  /generate      — Trang tạo QR (HTML)
  POST /api/scan-qr   — Quét QR từ ảnh (JPG/PNG/WEBP), trả về dữ liệu CCCD
  GET  /api/generate-qr — Tạo mã QR PNG chất lượng cao
  GET  /health        — Health check
  GET  /docs          — Swagger UI

Bảo mật:
  - Giới hạn kích thước file (MAX_SIZE)
  - Magic byte validation (JPEG, PNG, WEBP)
  - Pillow deep image verification
  - Rate limiting qua slowapi (mặc định 30 req/phút/IP)
  - CORS headers
"""

import io
import logging
import qrcode
import qrcode.image.pil
import logging.config
import os
import re
import sys

from contextlib import asynccontextmanager
from PIL import Image

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi.staticfiles import StaticFiles

from qr_engine import QREngine
from config import load_config

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
})

logger = logging.getLogger("QRServer")

# ---------------------------------------------------------------------------
# Server Config (loaded at startup from config.json)
# ---------------------------------------------------------------------------

_server_config: dict = {}
_qr_engine: QREngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo QR Engine và nạp config khi server start."""
    global _qr_engine, _server_config
    _server_config = load_config()
    logger.info("=== QR API Server đang khởi động ===")
    logger.info(f"Cổng: {_server_config.get('port', 8000)} | API Key: {'Bật' if _server_config.get('api_key_enabled') else 'Tắt'}")
    logger.info("Đang khởi tạo QR Engine (có thể mất vài giây nếu cần tải model)...")
    _qr_engine = QREngine()
    logger.info("=== QR API Server sẵn sàng phục vụ ===")
    yield
    logger.info("=== QR API Server đang tắt ===")
    _qr_engine = None


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="QR API Server",
    description=(
        "Server quét mã QR chuyên dụng — hỗ trợ đọc CCCD Việt Nam.\n\n"
        "**Engine decode đa tầng:**\n"
        "1. WeChat QR AI (Caffe model — mạnh nhất, chống mờ/chói)\n"
        "2. OpenCV Standard QRCodeDetector\n"
        "3. pyzbar (fallback)\n\n"
        "**Preprocessing pipeline:**\n"
        "CLAHE → Adaptive Threshold → Upscale (tự động chọn biến thể tốt nhất)"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS — cho phép gọi từ mọi nguồn (điều chỉnh origins nếu cần production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limit error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# ---------------------------------------------------------------------------
# Middlewares
# ---------------------------------------------------------------------------

@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Kiểm tra API Key cho các endpoint /api/* nếu đã bật."""
    path = request.url.path
    if path.startswith("/api/") and _server_config.get("api_key_enabled"):
        expected = _server_config.get("api_key", "")
        # Hỗ trợ cả header và query param (cho GET download)
        provided = (
            request.headers.get("X-API-Key", "")
            or request.query_params.get("api_key", "")
        )
        if not expected or provided != expected:
            return JSONResponse(
                {
                    "success": False,
                    "detail": "Thiếu hoặc sai API Key. Thêm header X-API-Key: <mã> vào request.",
                    "hint": "Lấy mã trong QR API Server Desktop App > Phần Bảo mật.",
                },
                status_code=401,
            )
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# HTML Page Routes
# ---------------------------------------------------------------------------

def _serve_html(filename: str) -> Response:
    """Phục vụ file HTML từ thư mục static.
    
    Nếu API Key được bật, tự động nhúc mã vào <meta> để JS có thể gửi kèm request.
    """
    path = os.path.join(_static_dir, filename)
    if not os.path.exists(path):
        return HTMLResponse("<h1>Page not found</h1>", status_code=404)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    # Inject API key vào HTML nếu được bật
    if _server_config.get("api_key_enabled") and _server_config.get("api_key"):
        key = _server_config["api_key"]
        content = content.replace(
            "</head>",
            f'<meta name="x-api-key" content="{key}">\n</head>',
            1,
        )
    return HTMLResponse(content)


@app.get("/", response_class=HTMLResponse, tags=["pages"], include_in_schema=False)
async def home():
    """Trang chủ — Landing page."""
    return _serve_html("index.html")


@app.get("/scan", response_class=HTMLResponse, tags=["pages"], include_in_schema=False)
async def scan_page():
    """Trang quét mã QR."""
    return _serve_html("scan.html")


@app.get("/generate", response_class=HTMLResponse, tags=["pages"], include_in_schema=False)
async def generate_page():
    """Trang tạo mã QR."""
    return _serve_html("generate.html")


@app.get("/health", tags=["info"])
async def health():
    """Health check — dùng để kiểm tra server còn sống không."""
    engine_ready = _qr_engine is not None
    wechat_ready = engine_ready and _qr_engine.detector_wechat is not None
    pyzbar_ready = engine_ready and _qr_engine._pyzbar_decode is not None

    return {
        "status": "ok" if engine_ready else "degraded",
        "version": "2.0.0",
        "engine": {
            "wechat_ai": wechat_ready,
            "opencv": engine_ready,
            "pyzbar": pyzbar_ready,
        },
    }


# ---------------------------------------------------------------------------
# QR Code Generation
# ---------------------------------------------------------------------------

EC_LEVEL_MAP = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}


@app.get("/api/generate-qr", tags=["qr"])
@limiter.limit("60/minute")
async def generate_qr(
    request: Request,
    data: str = Query(..., description="Nội dung mã QR", max_length=2000),
    size: int = Query(256, ge=64, le=1024, description="Kích thước ảnh PNG (px)"),
    error_correction: str = Query("M", description="Mức sửa lỗi: L / M / Q / H"),
    fg: str = Query("#000000", description="Màu QR (hex, vd: #000000)"),
    bg: str = Query("#ffffff", description="Màu nền (hex, vd: #ffffff)"),
):
    """
    Tạo mã QR và trả về ảnh PNG.

    **Ví dụ:**
    ```
    GET /api/generate-qr?data=https://example.com&size=512&error_correction=H&fg=%23000000&bg=%23ffffff
    ```
    """
    ec_level = EC_LEVEL_MAP.get(error_correction.upper(), qrcode.constants.ERROR_CORRECT_M)

    # Validate hex colors
    import re
    hex_pattern = re.compile(r'^#[0-9a-fA-F]{6}$')
    if not hex_pattern.match(fg): fg = "#000000"
    if not hex_pattern.match(bg): bg = "#ffffff"

    try:
        qr = qrcode.QRCode(
            version=None,  # Auto-select
            error_correction=ec_level,
            box_size=max(1, size // 25),
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        # Convert hex to RGB tuple
        def hex_to_rgb(h: str):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        img = qr.make_image(
            fill_color=hex_to_rgb(fg),
            back_color=hex_to_rgb(bg),
        ).convert('RGB')

        # Resize to exact requested size
        from PIL import Image as PILImage
        img = img.resize((size, size), PILImage.NEAREST)

        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=True)
        buf.seek(0)

        return Response(
            content=buf.read(),
            media_type="image/png",
            headers={
                "Content-Disposition": f'attachment; filename="qrcode_{size}x{size}.png"',
                "Cache-Control": "no-store",
            },
        )

    except Exception as e:
        logger.error(f"generate_qr error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "detail": f"Lỗi tạo mã QR: {str(e)}"},
            status_code=500,
        )


@app.post("/api/scan-qr", tags=["qr"])
@limiter.limit("30/minute")
async def scan_qr(request: Request, file: UploadFile = File(...)):
    """
    Quét mã QR từ ảnh.

    **Định dạng hỗ trợ:** JPG, PNG, WEBP

    **Giới hạn:** tối đa 10MB/ảnh, 30 request/phút/IP

    **Response thành công (CCCD):**
    ```json
    {
        "success": true,
        "cccd": "012345678901",
        "full_name": "NGUYEN VAN A",
        "dob": "01/01/1990",
        "gender": "Nam",
        "address": "...",
        "raw_data": "...",
        "method": "wechat_ai/original"
    }
    ```

    **Response thành công (QR thường):**
    ```json
    {"success": true, "raw_data": "...", "method": "opencv/gray"}
    ```
    """
    if _qr_engine is None:
        return JSONResponse(
            {"success": False, "detail": "QR Engine chưa sẵn sàng. Vui lòng thử lại sau."},
            status_code=503,
        )

    try:
        content = await file.read()

        # ── Bảo mật 1: Giới hạn kích thước ──────────────────────────────────
        MAX_SIZE = 10 * 1024 * 1024  # 10 MB
        if len(content) > MAX_SIZE:
            return JSONResponse(
                {"success": False, "detail": "Ảnh quá lớn. Vui lòng dùng ảnh dưới 10MB."},
                status_code=400,
            )

        # ── Bảo mật 2: Magic byte — chặn file rác đổi đuôi ──────────────────
        is_jpeg = content[:3] == b"\xff\xd8\xff"
        is_png  = content[:8] == b"\x89PNG\r\n\x1a\n"
        is_webp = content[:4] == b"RIFF" and b"WEBP" in content[8:16]

        if not (is_jpeg or is_png or is_webp):
            return JSONResponse(
                {"success": False, "detail": "Định dạng không hỗ trợ. Vui lòng dùng JPG, PNG hoặc WEBP."},
                status_code=400,
            )

        # ── Bảo mật 3: Pillow deep verify — phát hiện file hỏng/mã độc ──────
        try:
            img = Image.open(io.BytesIO(content))
            img.verify()
        except Exception:
            return JSONResponse(
                {"success": False, "detail": "File ảnh bị hỏng hoặc chứa dữ liệu không hợp lệ."},
                status_code=400,
            )

        # ── Decode QR ────────────────────────────────────────────────────────
        res = await _qr_engine.decode(content)

        if res.get("status") != "success":
            return JSONResponse(
                {"success": False, "detail": res.get("message", "Không nhận diện được mã QR.")},
                status_code=422,
            )

        raw_data = res.get("data", "")
        method   = res.get("method", "unknown")
        parts    = raw_data.split("|")

        # ── Parse dữ liệu CCCD (định dạng Bộ Công An) ────────────────────────
        # Format: <cccd>|<cmnd_cũ>|<họ_tên>|<ngày_sinh_DDMMYYYY>|<giới_tính>|<địa_chỉ>|...
        if len(parts) >= 6:
            dob_raw    = parts[3].strip()
            gender_raw = parts[4].strip().upper()
            gender     = (
                "Nam" if gender_raw == "NAM"
                else "Nữ" if gender_raw in ("NỮ", "NU")
                else gender_raw
            )
            dob_fmt = (
                f"{dob_raw[0:2]}/{dob_raw[2:4]}/{dob_raw[4:8]}"
                if len(dob_raw) == 8 else dob_raw
            )
            return {
                "success":   True,
                "cccd":      parts[0].strip(),
                "full_name": parts[2].strip(),
                "dob":       dob_fmt,
                "gender":    gender,
                "address":   parts[5].strip(),
                "raw_data":  raw_data,
                "method":    method,
            }

        # QR thông thường (không phải CCCD)
        return {"success": True, "raw_data": raw_data, "method": method}

    except Exception as e:
        logger.error(f"scan_qr critical error: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "detail": "Lỗi máy chủ khi xử lý ảnh."},
            status_code=500,
        )


# ---------------------------------------------------------------------------
# Entry point (chạy trực tiếp bằng python server.py hoặc run.ps1)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    cfg = load_config()
    port = int(os.environ.get("QR_SERVER_PORT", cfg.get("port", 8000)))
    host = os.environ.get("QR_SERVER_HOST", cfg.get("host", "0.0.0.0"))

    logger.info(f"Khởi động server tại http://{host}:{port}")
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
        access_log=True,
    )

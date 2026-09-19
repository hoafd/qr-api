"""
Config management cho QR API Server.
"""
import json
import os
import secrets
import string
import sys

# ── Đường dẫn config ──────────────────────────────────────────────────────────
# Khi chạy bình thường: cạnh file script
# Khi build .exe (PyInstaller): cạnh file .exe (không trong _MEIPASS)
if hasattr(sys, "_MEIPASS"):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(_BASE_DIR, "config.json")

DEFAULT_CONFIG: dict = {
    "port": 8000,
    "host": "0.0.0.0",
    "api_key_enabled": False,
    "api_key": "",
    "minimize_to_tray": True,
    "auto_start": False,
}


def generate_api_key(length: int = 12) -> str:
    """Sinh mã API key ngẫu nhiên gồm chữ + số."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def load_config() -> dict:
    """Đọc config.json. Tạo mới với giá trị mặc định nếu chưa tồn tại."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Điền giá trị mặc định cho các key còn thiếu
            for k, v in DEFAULT_CONFIG.items():
                data.setdefault(k, v)
            # Sinh key mới nếu trống
            if not data.get("api_key"):
                data["api_key"] = generate_api_key()
                _write(data)
            return data
        except Exception:
            pass  # File hỏng → tạo lại

    config = DEFAULT_CONFIG.copy()
    config["api_key"] = generate_api_key()
    _write(config)
    return config


def save_config(config: dict) -> None:
    """Lưu config xuống config.json."""
    _write(config)


def _write(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

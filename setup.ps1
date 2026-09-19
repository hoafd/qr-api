# =========================================================
#  QR API Server — Cài Đặt Môi Trường
# =========================================================
# Chuyển thư mục làm việc về vị trí của script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) { $ScriptDir = $PSScriptRoot }
if ($ScriptDir) { Set-Location -Path $ScriptDir }

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "       QR API SERVER — CÀI ĐẶT MÔI TRƯỜNG               " -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""

# ── Bước 1: Tạo .venv ──────────────────────────────────────────────────────
if (-not (Test-Path ".venv")) {
    Write-Host "[1/4] Tạo môi trường ảo (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      LỖI: Không tạo được .venv. Đảm bảo Python đã cài đặt." -ForegroundColor Red
        exit 1
    }
    Write-Host "      ✓ Môi trường ảo đã tạo." -ForegroundColor Green
} else {
    Write-Host "[1/4] Môi trường ảo (.venv) đã tồn tại." -ForegroundColor Green
}

$VENV_PYTHON = ".\.venv\Scripts\python.exe"
$VENV_PIP    = ".\.venv\Scripts\pip.exe"

# ── Bước 2: Nâng cấp pip ───────────────────────────────────────────────────
Write-Host ""
Write-Host "[2/4] Nâng cấp pip..." -ForegroundColor Yellow
& $VENV_PYTHON -m pip install --upgrade pip --quiet
Write-Host "      ✓ pip đã cập nhật." -ForegroundColor Green

# ── Bước 3: Cài đặt thư viện ───────────────────────────────────────────────
Write-Host ""
Write-Host "[3/4] Cài đặt thư viện từ requirements.txt..." -ForegroundColor Yellow
& $VENV_PIP install -r requirements.txt --default-timeout=120

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "      CẢNH BÁO: Một số gói cài đặt thất bại." -ForegroundColor Red
    Write-Host "      Thử lại thủ công: .venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
} else {
    Write-Host "      ✓ Tất cả thư viện đã cài đặt." -ForegroundColor Green
}

# ── Bước 4: Tải WeChat QR Model ────────────────────────────────────────────
Write-Host ""
Write-Host "[4/4] Kiểm tra và tải WeChat QR AI Model..." -ForegroundColor Yellow
Write-Host "      (Nếu đã có model, bước này bỏ qua ngay lập tức)" -ForegroundColor Gray

& $VENV_PYTHON -c @"
import sys, os
# Thêm thư mục hiện tại vào path để import qr_engine
sys.path.insert(0, os.getcwd())
from qr_engine import QREngine
engine = QREngine()
if engine.detector_wechat:
    print('      [OK] WeChat QR AI sẵn sàng.')
else:
    print('      [WARN] WeChat model chưa tải được (server vẫn chạy với OpenCV fallback).')
if engine._pyzbar_decode:
    print('      [OK] pyzbar sẵn sàng.')
else:
    print('      [INFO] pyzbar không khả dụng (không ảnh hưởng đến chức năng chính).')
"@

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " Cài đặt hoàn tất!" -ForegroundColor Green
Write-Host ""
Write-Host " Để khởi động server, chạy:" -ForegroundColor White
Write-Host "   .\run.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host " Hoặc chạy thủ công:" -ForegroundColor White
Write-Host "   .\.venv\Scripts\python.exe server.py" -ForegroundColor Yellow
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""

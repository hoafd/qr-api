# build.ps1 — Build QR API Server thành file .exe Windows
# ============================================================
# Sử dụng PyInstaller để đóng gói app.py thành thư mục dist/
#
# Cách dùng:
#   .\build.ps1
#
# Output: dist\QRAPIServer\QRAPIServer.exe
# ============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT = $PSScriptRoot

# ── Màu sắc output ──────────────────────────────────────────────────────────
function Info  { param($msg) Write-Host "  ℹ  $msg" -ForegroundColor Cyan }
function Ok    { param($msg) Write-Host "  ✓  $msg" -ForegroundColor Green }
function Warn  { param($msg) Write-Host "  ⚠  $msg" -ForegroundColor Yellow }
function Fail  { param($msg) Write-Host "  ✗  $msg" -ForegroundColor Red; exit 1 }
function Title { param($msg) Write-Host "`n━━  $msg  ━━" -ForegroundColor Magenta }

Title "QR API Server — Build"

# ── 1. Kiểm tra môi trường ảo ────────────────────────────────────────────────
$venv = Join-Path $ROOT ".venv"
if (-not (Test-Path "$venv\Scripts\python.exe")) {
    Fail "Không tìm thấy .venv. Chạy .\setup.ps1 trước."
}

$Python  = "$venv\Scripts\python.exe"
$PyInst  = "$venv\Scripts\pyinstaller.exe"

# Cài PyInstaller nếu chưa có
if (-not (Test-Path $PyInst)) {
    Info "Đang cài PyInstaller..."
    & $Python -m pip install pyinstaller --quiet
    if ($LASTEXITCODE -ne 0) { Fail "Không cài được PyInstaller." }
}

# Cài pystray nếu chưa có
Info "Kiểm tra pystray..."
& $Python -c "import pystray" 2>$null
if ($LASTEXITCODE -ne 0) {
    Info "Đang cài pystray..."
    & $Python -m pip install pystray --quiet
}

# ── 2. Kiểm tra các file bắt buộc ────────────────────────────────────────────
Title "Kiểm tra file nguồn"
foreach ($f in @("app.py", "server.py", "qr_engine.py", "config.py")) {
    if (Test-Path "$ROOT\$f") { Ok $f }
    else { Fail "Thiếu file: $f" }
}
if (Test-Path "$ROOT\static") { Ok "static/" }
else { Warn "Thư mục static/ không tồn tại — trang web sẽ không hoạt động." }

$hasModels = Test-Path "$ROOT\models"
if ($hasModels) { Ok "models/ (WeChat AI)" }
else { Warn "Thư mục models/ không tồn tại. WeChat AI sẽ không khả dụng." }

# ── 3. Xóa build cũ ─────────────────────────────────────────────────────────
Title "Dọn build cũ"
foreach ($dir in @("dist", "build")) {
    if (Test-Path "$ROOT\$dir") {
        Remove-Item "$ROOT\$dir" -Recurse -Force
        Ok "Đã xóa $dir/"
    }
}
if (Test-Path "$ROOT\QRAPIServer.spec") {
    Remove-Item "$ROOT\QRAPIServer.spec" -Force
}

# ── 4. Build ─────────────────────────────────────────────────────────────────
Title "Đang build..."

$addData = @(
    "--add-data", "static;static"
)

if ($hasModels) {
    $addData += "--add-data", "models;models"
}

$args_list = @(
    "app.py",
    "--name",    "QRAPIServer",
    "--onedir",
    "--noconsole",
    "--distpath", "$ROOT\dist",
    "--workpath", "$ROOT\build",
    "--specpath", "$ROOT"
) + $addData + @(
    "--hidden-import", "uvicorn.logging",
    "--hidden-import", "uvicorn.loops",
    "--hidden-import", "uvicorn.loops.auto",
    "--hidden-import", "uvicorn.protocols",
    "--hidden-import", "uvicorn.protocols.http",
    "--hidden-import", "uvicorn.protocols.http.auto",
    "--hidden-import", "uvicorn.protocols.websockets",
    "--hidden-import", "uvicorn.protocols.websockets.auto",
    "--hidden-import", "uvicorn.lifespan",
    "--hidden-import", "uvicorn.lifespan.on",
    "--hidden-import", "pystray._win32",
    "--hidden-import", "PIL._tkinter_finder",
    "--hidden-import", "slowapi",
    "--hidden-import", "qrcode",
    "--hidden-import", "qrcode.image.pil",
    "--hidden-import", "multipart",
    "--hidden-import", "qr_engine",
    "--hidden-import", "config",
    "--hidden-import", "server",
    "--collect-all",   "uvicorn",
    "--collect-all",   "fastapi",
    "--collect-all",   "starlette",
    "--collect-all",   "qrcode",
    "--collect-all",   "slowapi",
    "--collect-all",   "pyzbar",
    "--collect-all",   "cv2",
    "--noconfirm",
    "--clean"
)

& $PyInst @args_list

if ($LASTEXITCODE -ne 0) { Fail "PyInstaller thất bại! Xem log ở trên." }

# ── 5. Copy config.json mẫu vào dist (nếu chưa có) ──────────────────────────
$distDir = "$ROOT\dist\QRAPIServer"
if (Test-Path "$ROOT\config.json") {
    Copy-Item "$ROOT\config.json" "$distDir\config.json" -Force
    Ok "Đã copy config.json vào dist/"
}

# ── 6. Kết quả ───────────────────────────────────────────────────────────────
Title "Build hoàn tất!"
Ok "Thư mục output:  dist\QRAPIServer\"
Ok "File thực thi:   dist\QRAPIServer\QRAPIServer.exe"

Write-Host @"

  📦  Để phân phối, copy toàn bộ thư mục dist\QRAPIServer\ đến máy đích.
  ▶   Chạy QRAPIServer.exe để mở Desktop App và quản lý server.
  ⚙   config.json sẽ được tạo tự động bên cạnh file .exe.

"@ -ForegroundColor Cyan

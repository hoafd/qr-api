# =========================================================
#  QR API Server 2.0 — Khởi Động Ứng Dụng Desktop
# =========================================================
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) { $ScriptDir = $PSScriptRoot }
if ($ScriptDir) { Set-Location -Path $ScriptDir }

$VENV_PYTHON = ".\.venv\Scripts\python.exe"

# Kiểm tra môi trường ảo đã setup chưa
if (-not (Test-Path $VENV_PYTHON)) {
    Write-Host ""
    Write-Host "[LỖI] Chưa tìm thấy môi trường ảo (.venv)." -ForegroundColor Red
    Write-Host "      Vui lòng chạy setup trước: .\setup.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "Đang khởi chạy QR API Server Desktop App..." -ForegroundColor Cyan

# Khởi động app đồ họa
& $VENV_PYTHON app.py

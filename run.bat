:: Batch Script
@echo off
setlocal
echo ==============================================
echo        Khoi chay QR API Server
echo ==============================================

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Chua co moi truong ao. Dang tao .venv...
    python -m venv .venv
)

echo [INFO] Cai dat thu vien tu requirements.txt...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

echo [INFO] Dang khoi chay Server...
.venv\Scripts\python.exe runner.py
@echo off
setlocal
echo ==============================================
echo        Dong QR API Server
echo ==============================================

echo [INFO] Tim va dong tat ca cac tien trinh python lien quan den QR API...
taskkill /F /IM python.exe /T /FI "WINDOWTITLE eq QR API Server - Setup" 2>nul
taskkill /F /IM QR_API_Server.exe /T 2>nul

echo [INFO] Neu port van bi chiem, he thong se thu tim va dong tien trinh giu port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| find "8000" ^| find "LISTENING"') do (
    echo [INFO] Phat hien tien trinh %%a dang giu port 8000. Dang dong...
    taskkill /F /PID %%a 2>nul
)

echo [INFO] Hoan tat!
pause

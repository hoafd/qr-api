:: Batch Script
@echo off
setlocal
echo ==============================================
echo        Dong goi thanh .exe (Thu Muc)
echo ==============================================

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Chua co moi truong ao. Dang tao .venv...
    python -m venv .venv
)

echo [INFO] Cai dat cac thu vien can thiet...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install pyinstaller

set SITE_PACKAGES=.venv\Lib\site-packages

echo [INFO] Dang chay PyInstaller...
.venv\Scripts\pyinstaller.exe --noconfirm --onedir --noconsole ^
    --paths="%SITE_PACKAGES%" ^
    --collect-all=cv2 ^
    --collect-all=uvicorn ^
    --collect-all=fastapi ^
    --collect-all=starlette ^
    --collect-all=pystray ^
    --collect-all=pydantic ^
    --collect-all=email_validator ^
    --hidden-import=uvicorn.logging ^
    --hidden-import=uvicorn.loops ^
    --hidden-import=uvicorn.loops.auto ^
    --hidden-import=uvicorn.protocols ^
    --hidden-import=uvicorn.protocols.http ^
    --hidden-import=uvicorn.protocols.http.auto ^
    --hidden-import=uvicorn.protocols.websockets ^
    --hidden-import=uvicorn.protocols.websockets.auto ^
    --hidden-import=uvicorn.lifespan ^
    --hidden-import=uvicorn.lifespan.on ^
    --name=QR_API_Server ^
    runner.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build that bai!
    pause
    exit /b %ERRORLEVEL%
)

echo [INFO] Dang copy models va config...
set DIST_DIR=dist\QR_API_Server
set INTERNAL_DIR=%DIST_DIR%\_internal
set APP_DIR=%INTERNAL_DIR%\app

if not exist "%APP_DIR%\models" mkdir "%APP_DIR%\models"
xcopy /E /I /Y "app\models" "%APP_DIR%\models" >nul

if exist "config.json" copy /Y "config.json" "%INTERNAL_DIR%" >nul

echo ==============================================
echo [INFO] Build Complete! Ung dung cua ban nam trong thu muc:
echo        %cd%\%DIST_DIR%
echo ==============================================
pause

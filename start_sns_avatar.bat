@echo off
cd /d "%~dp0"

REM SNS Avatar 프로세스만 종료 (PID 파일 사용)
if exist "data\sns_avatar.pid" (
    for /f %%i in (data\sns_avatar.pid) do taskkill /f /pid %%i >nul 2>&1
    timeout /t 2 /nobreak >nul
    del /q "data\sns_avatar.pid" 2>nul
)

del /q logs\*.log 2>nul
python src/main.py
@echo off
cd /d "%~dp0"
taskkill /f /im python.exe 2>nul
timeout /t 60 /nobreak >nul
del /q logs\*.log 2>nul
python src/main.py


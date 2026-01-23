@echo off
REM SNS Avatar 종료 배치 파일

cd /d "C:\Users\Mini PC\OneDrive\문서\SNS Avatar"

REM 날짜 추출 (한글 Windows 호환)
for /f "tokens=1-3 delims=. " %%a in ("%date%") do (
    set YEAR=%%a
    set MONTH=%%b
    set DAY=%%c
)
set LOG_FILE=logs\scheduler_%YEAR%%MONTH%%DAY%.log

echo [%date% %time%] SNS Avatar 종료 >> "%LOG_FILE%"

REM Python 프로세스 종료
taskkill /f /im python.exe 2>nul

echo SNS Avatar가 종료되었습니다.

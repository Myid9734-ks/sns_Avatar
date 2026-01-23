@echo off
REM SNS Avatar 자동 실행 배치 파일
REM Windows 작업 스케줄러용

REM 작업 디렉토리 설정
cd /d "C:\Users\Mini PC\OneDrive\문서\SNS Avatar"

REM 로그 폴더 생성 (없으면)
if not exist logs mkdir logs

REM 날짜 추출 (한글 Windows 호환)
for /f "tokens=1-3 delims=. " %%a in ("%date%") do (
    set YEAR=%%a
    set MONTH=%%b
    set DAY=%%c
)
set LOG_FILE=logs\scheduler_%YEAR%%MONTH%%DAY%.log

REM 3일 이상 된 로그 파일 삭제
forfiles /p "logs" /s /m *.log /d -3 /c "cmd /c del @path" 2>nul

REM 시작 시간 기록
echo ============================================== >> "%LOG_FILE%"
echo [%date% %time%] SNS Avatar 시작 >> "%LOG_FILE%"
echo ============================================== >> "%LOG_FILE%"

REM Python 실행
python src/main.py >> "%LOG_FILE%" 2>&1

REM 종료 시간 기록
echo [%date% %time%] SNS Avatar 종료 >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

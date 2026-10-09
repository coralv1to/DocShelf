@echo off
rem ======================================================================
rem  DocShelf - CHAY UNG DUNG
rem    run.bat        chi may nay vao duoc: http://localhost:8000
rem    run.bat lan    may khac cung mang LAN vao duoc: http://<IP-may-nay>:8000
rem  Dung: bam Ctrl+C trong cua so nay (hoac dong cua so).
rem ======================================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

if not exist backend\.venv\Scripts\python.exe (
    echo [LOI] Chua cai dat. Bam dup setup.bat truoc.
    pause
    exit /b 1
)

rem ---- Postgres (Docker): tu bat neu chua chay
docker compose up -d >nul 2>nul || echo [CANH BAO] Khong bat duoc Postgres. Mo Docker Desktop roi chay lai run.bat.

rem ---- Ollama: kiem tra dang chay
curl -s -o nul http://127.0.0.1:11434 || echo [CANH BAO] Ollama chua chay. Mo ung dung Ollama, neu khong se khong tra loi duoc cau hoi.

set HOST=127.0.0.1
if /i "%~1"=="lan" set HOST=0.0.0.0

echo.
echo  DocShelf dang khoi dong... trinh duyet se tu mo http://localhost:8000
echo  (Lan dau khoi dong mat 20-60 giay de nap san model. Dung: Ctrl+C)
echo.

rem Mo trinh duyet sau vai giay, cho server kip chay
start "" cmd /c "timeout /t 8 /nobreak >nul & start http://localhost:8000"

cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host %HOST% --port 8000
pause

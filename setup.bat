@echo off
rem ======================================================================
rem  DocShelf - CAI DAT LAN DAU (chi can chay 1 lan)
rem  Can co san: Docker Desktop (dang mo), Python 3.12+, Ollama
rem ======================================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo.
echo  ===== DocShelf - cai dat lan dau =====
echo.

rem ---- Kiem tra phan mem can co
where docker >nul 2>nul || (echo [LOI] Chua cai Docker Desktop: https://www.docker.com/products/docker-desktop/ & goto :fail)
where python >nul 2>nul || (echo [LOI] Chua cai Python 3.12+: https://www.python.org/downloads/  - nho tick "Add python.exe to PATH" & goto :fail)
where ollama >nul 2>nul || (echo [LOI] Chua cai Ollama: https://ollama.com/download & goto :fail)

echo [1/7] Bat Postgres bang Docker...
docker compose up -d || (echo [LOI] Khong chay duoc Docker. Mo Docker Desktop, doi no chay xong roi chay lai setup.bat & goto :fail)

cd backend
echo.
echo [2/7] Tao moi truong Python rieng (backend\.venv)...
if not exist .venv\Scripts\python.exe (
    python -m venv .venv || goto :fail
) else (
    echo    Da co .venv, dung lai.
)

echo.
echo [3/7] Cai thu vien Python (lan dau mat 3-10 phut)...
.venv\Scripts\python.exe -m pip install --upgrade pip >nul
.venv\Scripts\python.exe -m pip install -r requirements.txt || goto :fail

echo.
echo [4/7] Tao file cau hinh backend\.env...
.venv\Scripts\python.exe -m tools.setup_env || goto :fail

echo.
echo [5/7] Doi Postgres san sang roi tao bang...
set tries=0
:waitdb
docker exec docshelf-db pg_isready -U docshelf -d docshelf >nul 2>nul && goto :dbready
set /a tries+=1
if %tries% geq 30 (echo [LOI] Postgres chua san sang sau 60 giay. Xem: docker compose ps & goto :fail)
timeout /t 2 /nobreak >nul
goto :waitdb
:dbready
.venv\Scripts\python.exe -m alembic upgrade head || goto :fail

echo.
echo [6/7] Tai model AI cho Ollama (lan dau khoang 3.5GB)...
for /f "delims=" %%m in ('.venv\Scripts\python.exe -m tools.setup_env --models') do (
    echo    ollama pull %%m
    ollama pull %%m || goto :fail
)

echo.
echo [7/7] Tao tai khoan quan tri (admin)
choice /c YN /m "   Tao tai khoan admin ngay bay gio"
if errorlevel 2 goto :done
.venv\Scripts\python.exe -m app.cli create-user admin --role admin
if errorlevel 1 echo    (Neu bao tai khoan da ton tai thi bo qua, dung tai khoan cu.)

:done
echo.
echo  ===== XONG! =====
echo  - Chay ung dung: bam dup run.bat (o thu muc goc)
echo  - Tao them nguoi dung: cd backend  roi  .venv\Scripts\python.exe -m app.cli create-user ten
echo  - Lan dau hoi, backend con tai them reranker (~2.2GB), cho mot chut.
echo.
pause
exit /b 0

:fail
echo.
echo  ===== CAI DAT CHUA XONG - xem loi o tren =====
echo.
pause
exit /b 1

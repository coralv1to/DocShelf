@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
echo Dang chay bo cau hoi Triet hoc (184 luot, khoang 1 gio). Tien do ghi vao eval\triet_log.txt
echo Lan dau sau khi cap nhat code: doc lai PDF bang bo cat doan moi (them vai phut).
echo === BAT DAU %date% %time% > eval\triet_log.txt
".venv\Scripts\python.exe" -u -m eval.run_triet_hoc --reparse %* >> eval\triet_log.txt 2>&1
echo === ollama ps >> eval\triet_log.txt
ollama ps >> eval\triet_log.txt 2>&1
echo === KET THUC %date% %time% >> eval\triet_log.txt
echo Xong. Bao cao o eval\reports\triet_*.md. Co the dong cua so nay.
pause

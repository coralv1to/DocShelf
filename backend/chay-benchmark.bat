@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
echo Dang chay benchmark (15-40 phut). Tien do ghi vao eval\bench_log.txt
echo === ollama ps truoc khi chay > eval\bench_log.txt
ollama ps >> eval\bench_log.txt 2>&1
".venv\Scripts\python.exe" -u -m eval.run_bench --pdf sample.pdf >> eval\bench_log.txt 2>&1
echo === ollama ps sau khi chay >> eval\bench_log.txt
ollama ps >> eval\bench_log.txt 2>&1
echo === XONG >> eval\bench_log.txt
echo Xong. Co the dong cua so nay.
pause

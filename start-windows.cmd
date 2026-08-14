@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m roi_web --host 127.0.0.1 --port 8877
  exit /b %errorlevel%
)
where python >nul 2>nul
if %errorlevel%==0 (
  python -m roi_web --host 127.0.0.1 --port 8877
  exit /b %errorlevel%
)
echo 未找到 Python 3。请先安装 Python 3.9–3.12，并安装 requirements-roi-workbench.txt。
pause

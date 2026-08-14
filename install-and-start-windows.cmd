@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_and_start_windows.ps1"
if errorlevel 1 (
  echo.
  echo 安装或启动失败，请把上面的错误信息发给 Codex。
  pause
)

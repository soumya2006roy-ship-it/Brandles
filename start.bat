@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "MODE=dev"
if /I "%~1"=="prod" set "MODE=prod"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch-brandlens.ps1" -Mode "%MODE%"
if errorlevel 1 (
  pause
  exit /b 1
)
exit /b 0

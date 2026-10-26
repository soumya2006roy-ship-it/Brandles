@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "CONTAINERS="
if /I "%~1"=="containers" set "CONTAINERS=-Containers"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-brandlens.ps1" %CONTAINERS%
if errorlevel 1 exit /b 1
exit /b 0

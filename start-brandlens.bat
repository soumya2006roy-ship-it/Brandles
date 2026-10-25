@echo off
setlocal
cd /d "%~dp0"

where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo npm was not found. Install Node.js 20.9 or newer, then try again.
  pause
  exit /b 1
)

where docker >nul 2>&1
if not errorlevel 1 (
  docker info >nul 2>&1
  if not errorlevel 1 (
    echo Starting the BrandLens website and product services with Docker Compose...
    start "BrandLens product stack" /D "%~dp0" cmd /k "docker compose up --build"
    timeout /t 8 /nobreak >nul
    start "" "http://localhost:3000"
    endlocal
    exit /b 0
  )
)

echo Docker is unavailable. Starting the public marketing site only.
echo The organisation workspace needs Docker Desktop and the full product stack.
if not exist "node_modules" (
  echo Installing project dependencies...
  call npm.cmd install
  if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
  )
)

start "BrandLens marketing site" /D "%~dp0" cmd /k "npm.cmd run dev"
timeout /t 4 /nobreak >nul
start "" "http://localhost:3000"
endlocal

@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker CLI was not found. Install Docker Desktop with Compose, start it, and try again.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not running. Start it, wait for the engine, and try again.
  pause
  exit /b 1
)

docker compose version >nul 2>&1
if errorlevel 1 (
  echo Docker Compose is unavailable. Update Docker Desktop and try again.
  pause
  exit /b 1
)

echo Building and starting the complete BrandLens stack...
docker compose up --build -d
if errorlevel 1 goto compose_failed

echo Waiting for the API, database, Redis, and website to become ready...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\wait-for-brandlens.ps1"
if errorlevel 1 goto readiness_failed

echo BrandLens is ready. Opening the sign-in page.
start "" "http://localhost:3000/login"
start "BrandLens service logs" /D "%~dp0" cmd /k "docker compose logs --follow web api worker"
endlocal
exit /b 0

:compose_failed
echo Docker Compose failed to start the BrandLens services. Recent service output:
docker compose ps
docker compose logs --tail 80 web api worker db redis minio minio-init mailpit
pause
exit /b 1

:readiness_failed
echo BrandLens did not become ready within the allowed time. Recent service output:
docker compose ps
docker compose logs --tail 80 web api worker db redis minio minio-init mailpit
pause
exit /b 1

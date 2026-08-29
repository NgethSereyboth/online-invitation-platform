@echo off
setlocal
cd /d "%~dp0"
title E-invitation-website - Full Docker Stack

where docker >nul 2>nul
if errorlevel 1 (
  echo Docker is not installed or is not in PATH.
  echo Run SETUP_EINVITE_COMPLETE.bat first.
  pause
  exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
  echo Docker Desktop is installed but the Docker engine is not running.
  echo Start Docker Desktop, wait until it says Docker is running, then try again.
  pause
  exit /b 1
)

echo Building and starting:
echo   - E-invitation application
echo   - PostgreSQL 16
echo   - Redis 7
echo.

docker compose -f docker-compose.local.yml up --build -d
if errorlevel 1 (
  echo Docker stack failed to start.
  pause
  exit /b 1
)

echo Waiting for the application...
powershell -NoProfile -Command "$deadline=(Get-Date).AddMinutes(2); do { try { $r=Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8080/api/health' -TimeoutSec 2; if($r.StatusCode -eq 200){exit 0} } catch{}; Start-Sleep -Seconds 2 } while((Get-Date)-lt $deadline); exit 1"

start "" "http://127.0.0.1:8080"
echo.
echo Full production-like local stack is running at:
echo http://127.0.0.1:8080
echo.
echo Use STOP_EINVITE_FULL_DOCKER_STACK.bat to stop it.
pause

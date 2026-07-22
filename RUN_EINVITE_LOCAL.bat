@echo off
setlocal
cd /d "%~dp0"
title E-invitation-website - Local Server

if not exist ".venv\Scripts\python.exe" (
  echo The project environment is not installed yet.
  echo Run SETUP_EINVITE_COMPLETE.bat first.
  pause
  exit /b 1
)

set "EINVITE_DATA_DIR=%CD%\data"
set "EINVITE_PUBLIC_BASE_URL=http://127.0.0.1:8080"
set "EINVITE_COOKIE_SECURE=0"
set "EINVITE_DEV_AUTH_TOKENS=1"
set "EINVITE_ENFORCE_PLAN_LIMITS=0"

start "" powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8080'"

echo ============================================================
echo E-invitation-website is starting locally.
echo.
echo Address: http://127.0.0.1:8080
echo.
echo Keep this window open while using the website.
echo Press Ctrl+C here when you want to stop the server.
echo ============================================================
echo.

".venv\Scripts\python.exe" -u server.py --host 127.0.0.1 --port 8080
pause

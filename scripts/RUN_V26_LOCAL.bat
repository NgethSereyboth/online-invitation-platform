@echo off
setlocal
cd /d "%~dp0"
title E-Invitation Platform V26 - Local Studio
if not exist ".venv\Scripts\python.exe" (
  echo The local environment is not installed.
  echo Run SETUP_EINVITE_COMPLETE.bat first.
  pause
  exit /b 1
)
call V26_WINDOWS_READINESS.bat
if errorlevel 1 exit /b 1
set "EINVITE_DATA_DIR=%CD%\data"
set "EINVITE_PUBLIC_BASE_URL=http://127.0.0.1:8080"
set "EINVITE_COOKIE_SECURE=0"
set "EINVITE_DEV_AUTH_TOKENS=1"
set "EINVITE_ENFORCE_PLAN_LIMITS=0"
start "" powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8080'"
".venv\Scripts\python.exe" -u server.py --host 127.0.0.1 --port 8080
pause

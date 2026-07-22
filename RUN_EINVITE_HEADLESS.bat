@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" exit /b 1
if not exist "data" mkdir "data"
set "EINVITE_DATA_DIR=%CD%\data"
set "EINVITE_PUBLIC_BASE_URL=http://127.0.0.1:8080"
set "EINVITE_COOKIE_SECURE=0"
set "EINVITE_DEV_AUTH_TOKENS=0"
".venv\Scripts\python.exe" -u server.py --host 0.0.0.0 --port 8080 >> "data\server-headless.log" 2>&1

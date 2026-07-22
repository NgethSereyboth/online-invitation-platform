@echo off
setlocal
cd /d "%~dp0"
title E-invitation-website - Network Server

if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP_EINVITE_COMPLETE.bat first.
  pause
  exit /b 1
)

for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$ip=(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue ^| Where-Object {$_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -ne 'WellKnown'} ^| Select-Object -First 1 -ExpandProperty IPAddress); if($ip){$ip}else{'YOUR-PC-IP'}"`) do set "LOCALIP=%%I"

set "EINVITE_DATA_DIR=%CD%\data"
set "EINVITE_PUBLIC_BASE_URL=http://%LOCALIP%:8080"
set "EINVITE_COOKIE_SECURE=0"
set "EINVITE_DEV_AUTH_TOKENS=1"

echo ============================================================
echo E-invitation-website network mode
echo.
echo This computer: http://127.0.0.1:8080
echo Other devices: http://%LOCALIP%:8080
echo.
echo The other device must be on the same private network/Wi-Fi.
echo Keep this window open. Press Ctrl+C to stop.
echo ============================================================
echo.

start "" "http://127.0.0.1:8080"
".venv\Scripts\python.exe" -u server.py --host 0.0.0.0 --port 8080
pause

@echo off
setlocal
cd /d "%~dp0"
title E-invitation-website - Public HTTPS Tunnel

if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP_EINVITE_COMPLETE.bat first.
  pause
  exit /b 1
)

where cloudflared >nul 2>nul
if errorlevel 1 (
  echo Cloudflare Tunnel is not installed or not in PATH.
  echo Run SETUP_EINVITE_COMPLETE.bat again, or install cloudflared with winget.
  pause
  exit /b 1
)


echo Starting the local application in another window...
start "E-invitation Tunnel Server" "%CD%\RUN_EINVITE_TUNNEL_SERVER.bat"

echo Waiting for the local server...
powershell -NoProfile -Command "$deadline=(Get-Date).AddSeconds(30); do { try { $r=Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8080/api/health' -TimeoutSec 2; if($r.StatusCode -eq 200){exit 0} } catch{}; Start-Sleep -Milliseconds 700 } while((Get-Date)-lt $deadline); exit 1"
if errorlevel 1 (
  echo The local server did not become ready.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo Cloudflare will print a temporary public HTTPS URL below.
echo Share that URL only with people you trust during testing.
echo This temporary URL changes whenever the tunnel restarts.
echo Press Ctrl+C to stop the public tunnel.
echo ============================================================
echo.

cloudflared tunnel --url http://127.0.0.1:8080
pause

@echo off
setlocal
cd /d "%~dp0"

:: Self-elevate so winget installers and the firewall rule can complete cleanly.
net session >nul 2>&1
if errorlevel 1 (
  echo Requesting administrator permission...
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

title E-invitation-website - Complete Setup

echo ============================================================
echo   E-invitation-website - One Click Windows Setup
echo ============================================================
echo.
echo This will install and configure the software needed to:
echo   - Run the project locally
echo   - Run automated browser/review tests
echo   - Host it on your local network
echo   - Create a temporary public HTTPS tunnel
echo   - Run a production-like Docker stack with PostgreSQL/Redis
echo.
echo Administrator permission may be requested by Windows.
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-einvite-complete.ps1"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo ============================================================
  echo   Setup completed successfully.
  echo ============================================================
  echo.
  echo The project will open automatically if the local server started.
  echo You can later double-click RUN_EINVITE_LOCAL.bat.
) else (
  echo ============================================================
  echo   Setup did not complete successfully. Exit code: %EXITCODE%
  echo ============================================================
  echo.
  echo Open setup-einvite.log in this folder for details.
)
echo.
pause
exit /b %EXITCODE%

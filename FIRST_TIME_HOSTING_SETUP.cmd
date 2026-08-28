@echo off
setlocal
cd /d "%~dp0"
title E-invitation Platform - First Time Hosting Setup

if "%~1"=="" goto :usage

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-hosting-once.ps1" -Mode %*
set "EXITCODE=%ERRORLEVEL%"
echo.
if "%EXITCODE%"=="0" (
  echo FIRST_TIME_HOSTING_SETUP_COMPLETE
) else (
  echo FIRST_TIME_HOSTING_SETUP_STOPPED with exit code %EXITCODE%.
  echo Read FIRST_TIME_INSTALL_AND_HOSTING.md for the required next step.
)
exit /b %EXITCODE%

:usage
echo ============================================================
echo   E-invitation Platform - First Time Hosting Setup
echo ============================================================
echo.
echo Usage:
echo   FIRST_TIME_HOSTING_SETUP.cmd Validate
echo   FIRST_TIME_HOSTING_SETUP.cmd Local
echo   FIRST_TIME_HOSTING_SETUP.cmd Network
echo   FIRST_TIME_HOSTING_SETUP.cmd Docker -Domain invite.example.com
echo   FIRST_TIME_HOSTING_SETUP.cmd WindowsServer -Domain invite.example.com -CaddyExe C:\Tools\caddy.exe
echo.
echo Local and Network keep running in this window.
echo Docker requires Docker Desktop or Docker Engine with Compose v2.
echo WindowsServer requires Administrator access and external durable services.
echo.
exit /b 2

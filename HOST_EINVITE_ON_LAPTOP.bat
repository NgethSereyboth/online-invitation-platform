@echo off
setlocal
cd /d "%~dp0"
title E-invitation Platform - Laptop Host

echo ============================================================
echo   E-invitation Platform - One-command laptop hosting
echo ============================================================
echo.
echo The first run may install Python packages and request permission
echo for private-network firewall access. Keep this window open while
echo the website is being hosted.
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0host-einvite-laptop.ps1" %*
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
  echo.
  echo Laptop hosting stopped with exit code %EXITCODE%.
  echo Review the message above, then run this file again.
  pause
)
exit /b %EXITCODE%

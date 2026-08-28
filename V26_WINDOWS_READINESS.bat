@echo off
setlocal
cd /d "%~dp0"
title E-Invitation Platform V26 - Windows Readiness
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0V26_WINDOWS_READINESS.ps1" -StartHealthCheck
set CODE=%ERRORLEVEL%
echo.
if not "%CODE%"=="0" echo Review the items marked Action needed, then run this check again.
pause
exit /b %CODE%

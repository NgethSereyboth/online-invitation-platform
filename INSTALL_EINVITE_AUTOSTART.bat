@echo off
setlocal
cd /d "%~dp0"
title E-invitation-website - Install Auto Start

if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP_EINVITE_COMPLETE.bat first.
  pause
  exit /b 1
)

set "TASKNAME=E-invitation-website Local Host"
set "RUNNER=%CD%\RUN_EINVITE_HEADLESS.bat"

schtasks /Create /TN "%TASKNAME%" /TR "\"%RUNNER%\"" /SC ONLOGON /RL HIGHEST /F
if errorlevel 1 (
  echo The startup task could not be created. Try running this file as Administrator.
  pause
  exit /b 1
)

echo.
echo Auto-start installed.
echo The website will start at Windows sign-in and listen on port 8080.
echo Use REMOVE_EINVITE_AUTOSTART.bat to remove this behavior.
pause

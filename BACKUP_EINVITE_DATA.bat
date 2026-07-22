@echo off
setlocal
cd /d "%~dp0"
title E-invitation-website - Backup

if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP_EINVITE_COMPLETE.bat first.
  pause
  exit /b 1
)

set "EINVITE_DATA_DIR=%CD%\data"
".venv\Scripts\python.exe" backup.py

echo.
echo Backup command finished.
echo.
pause

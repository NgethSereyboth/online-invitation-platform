@echo off
setlocal
cd /d "%~dp0"
title E-invitation-website - Review Tests

if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP_EINVITE_COMPLETE.bat first.
  pause
  exit /b 1
)

set "EINVITE_DATA_DIR=%CD%\data-test"

echo Running complete deterministic review checks...
echo.
".venv\Scripts\python.exe" run_review_checks.py
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo All available review checks completed successfully.
) else (
  echo One or more checks reported a failure or environment limitation.
)
echo.
pause
exit /b %RESULT%

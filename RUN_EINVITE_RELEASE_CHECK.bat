@echo off
setlocal
cd /d "%~dp0"
title E-invitation-website - V9 Release Check

if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP_EINVITE_COMPLETE.bat first.
  pause
  exit /b 1
)

set "EINVITE_DATA_DIR=%CD%\data-test"

echo ============================================================
echo   E-invitation-website - V9 Full Release Check
echo ============================================================
echo.
echo This rebuilds generated editor files and runs all available
echo syntax, backend, security, collaboration, responsive-layout,
echo public-invitation, and real-browser regression checks.
echo.
".venv\Scripts\python.exe" release_check.py
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo V9 release verification completed successfully.
) else (
  echo Release verification failed. Review the first failing test above.
)
echo.
pause
exit /b %RESULT%

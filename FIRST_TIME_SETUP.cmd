@echo off
setlocal
cd /d "%~dp0"

title E-invitation Platform - First Time Setup

if not exist "%~dp0server.py" (
  echo ERROR: server.py was not found beside this setup file.
  echo Extract the complete project folder before running setup.
  pause
  exit /b 2
)

echo ============================================================
echo   E-invitation Platform - First Time Computer Setup
echo ============================================================
echo.
echo This installs or configures Python, an isolated project
echo environment, production libraries, local data folders, and
echo optional Windows tools. It is safe to run again after updates.
echo.
echo Automated browser-test software is not installed by this
echo quick setup. Use SETUP_EINVITE_COMPLETE.bat when you also want
echo the complete developer and browser-testing toolchain.
echo.

net session >nul 2>&1
if errorlevel 1 (
  echo Requesting administrator permission...
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-einvite-complete.ps1" -SkipBrowserTests -NoAutoStart %*
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo FIRST_TIME_SETUP_COMPLETE
  echo Run RUN_EINVITE_LOCAL.bat to open the website on this computer.
  echo Run FIRST_TIME_HOSTING_SETUP.cmd for network or permanent hosting.
) else (
  echo FIRST_TIME_SETUP_FAILED with exit code %EXITCODE%.
  echo Review setup-einvite.log in this folder.
)
echo.
pause
exit /b %EXITCODE%

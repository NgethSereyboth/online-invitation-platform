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

REM ===========================================================================
REM V54 security hardening: set dev-safe defaults BEFORE launching the app.
REM These mirror the .ps1 launcher's own settings so that even a direct
REM "python server.py" invocation sees the same protection.
REM ===========================================================================
set "EINVITE_COOKIE_SECURE=0"
set "EINVITE_ALLOWED_HOSTS=localhost 127.0.0.1"
set "EINVITE_ALLOW_NO_SCANNER=0"

REM ---------------------------------------------------------------------------
REM Windows Defender availability check. The backend's security_scanner_v54
REM module locates MpCmdRun.exe under %ProgramData%\Microsoft\Windows Defender
REM and uses it to scan every upload. If Defender is missing the server will
REM refuse to start (because EINVITE_ALLOW_NO_SCANNER=0 above). Echo a clear
REM warning so the operator can enable Defender before retrying.
REM ---------------------------------------------------------------------------
set "DEFENDER_CLI="
if exist "%ProgramData%\Microsoft\Windows Defender\Platform" (
  for /f "delims=" %%D in ('dir /b /ad /o-n "%ProgramData%\Microsoft\Windows Defender\Platform\" 2^>nul') do (
    if not defined DEFENDER_CLI if exist "%ProgramData%\Microsoft\Windows Defender\Platform\%%D\MpCmdRun.exe" (
      set "DEFENDER_CLI=%ProgramData%\Microsoft\Windows Defender\Platform\%%D\MpCmdRun.exe"
    )
  )
)
if not defined DEFENDER_CLI if exist "%ProgramFiles%\Windows Defender\MpCmdRun.exe" (
  set "DEFENDER_CLI=%ProgramFiles%\Windows Defender\MpCmdRun.exe"
)
if not defined DEFENDER_CLI (
  where.exe MpCmdRun.exe >nul 2>&1 && (
    for /f "delims=" %%P in ('where.exe MpCmdRun.exe') do if not defined DEFENDER_CLI set "DEFENDER_CLI=%%P"
  )
)
if not defined DEFENDER_CLI (
  echo [WARN] Microsoft Defender MpCmdRun.exe was not found on this laptop.
  echo        Uploads are scanned with Defender via security_scanner_v54.
  echo        Enable Windows Security (Virus ^& threat protection^) before
  echo        continuing, or set EINVITE_ALLOW_NO_SCANNER=1 in this script
  echo        to bypass at your own risk.
  echo.
)
if defined DEFENDER_CLI (
  echo [INFO] Windows Defender scanner located. Uploads will be scanned.
  echo        MpCmdRun.exe: %DEFENDER_CLI%
  echo.
)

REM ---------------------------------------------------------------------------
REM Secret bootstrap guidance. secrets_v54.py auto-generates strong values
REM for EINVITE_SECRET_KEY and EINVITE_BILLING_WEBHOOK_SECRET on the first
REM launch (when they are missing from .env / the environment) and appends
REM the generated values to the repo-root .env file. Pin them in .env before
REM the first launch if you need a stable secret across laptop restarts.
REM ---------------------------------------------------------------------------
echo [INFO] On first launch, the backend auto-generates:
echo         - EINVITE_SECRET_KEY
echo         - EINVITE_BILLING_WEBHOOK_SECRET
echo        Values are written into the repo-root .env file. Back up .env
echo        regularly; rotate the values by deleting the lines in .env.
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

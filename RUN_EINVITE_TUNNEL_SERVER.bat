@echo off
setlocal
cd /d "%~dp0"
title E-invitation-website - Tunnel Server
if not exist ".venv\Scripts\python.exe" exit /b 1
set "EINVITE_DATA_DIR=%CD%\data"
set "EINVITE_PUBLIC_BASE_URL="
set "EINVITE_COOKIE_SECURE=0"
set "EINVITE_DEV_AUTH_TOKENS=0"
set "EINVITE_ENFORCE_PLAN_LIMITS=0"
".venv\Scripts\python.exe" -u server.py --host 127.0.0.1 --port 8080

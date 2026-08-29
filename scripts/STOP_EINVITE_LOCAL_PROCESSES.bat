@echo off
setlocal
title E-invitation-website - Stop Local Processes

echo Stopping E-invitation Python servers and temporary Cloudflare tunnels...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { ($_.Name -match 'python') -and ($_.CommandLine -match 'server.py') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-CimInstance Win32_Process | Where-Object { ($_.Name -match 'cloudflared') -and ($_.CommandLine -match '127.0.0.1:8080') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

echo Done.
pause

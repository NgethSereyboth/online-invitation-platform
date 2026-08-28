@echo off
setlocal
cd /d "%~dp0"
title E-invitation-website - Stop Docker Stack

docker compose -f docker-compose.local.yml down

echo.
echo Docker stack stopped. Database and uploaded data remain in Docker volumes.
pause

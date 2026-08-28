@echo off
setlocal
title E-invitation-website - Remove Auto Start
schtasks /Delete /TN "E-invitation-website Local Host" /F
if errorlevel 1 (
  echo The task was not found or could not be removed.
) else (
  echo Auto-start removed.
)
pause

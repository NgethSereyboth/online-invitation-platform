@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "test-results\v20" mkdir "test-results\v20"
for %%R in (1 2 3) do (
  echo === V20 Windows gate run %%R/3 ===
  py -3 release_check.py > "test-results\v20\windows-release-gate-%%R.log" 2>&1
  if errorlevel 1 (
    type "test-results\v20\windows-release-gate-%%R.log"
    exit /b 1
  )
  type "test-results\v20\windows-release-gate-%%R.log"
)
echo V20 Windows gate passed three times.

@echo off
setlocal
cd /d "%~dp0"
for %%R in (1 2 3) do (
  echo Running V23.6.3 release gate %%R of 3...
  python release_check.py > "V23_6_RELEASE_WINDOWS_FINAL_%%R.txt" 2>&1
  if errorlevel 1 (
    type "V23_6_RELEASE_WINDOWS_FINAL_%%R.txt"
    exit /b 1
  )
)
echo V23.6.3 passed three Windows release-gate runs.
endlocal

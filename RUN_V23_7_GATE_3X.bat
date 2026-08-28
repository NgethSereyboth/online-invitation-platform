@echo off
setlocal
cd /d "%~dp0"
for /L %%I in (1,1,3) do (
  echo V23.7.3 release gate run %%I of 3
  py -3 release_check.py
  if errorlevel 1 exit /b %errorlevel%
)
echo V23.7.3 three-run Windows gate passed.
endlocal

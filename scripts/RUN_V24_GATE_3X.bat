@echo off
setlocal
cd /d "%~dp0"
for /L %%I in (1,1,3) do (
  echo V24.6.3 release gate run %%I of 3
  python release_check.py || exit /b 1
)
echo V24.6.3 three-run Windows gate passed.

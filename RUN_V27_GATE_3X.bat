@echo off
setlocal
cd /d "%~dp0"
for /L %%I in (1,1,3) do (
  echo V27.3.5 release gate run %%I of 3
  python release_check.py || exit /b 1
)
echo V27.3.5 three-run Windows gate passed.

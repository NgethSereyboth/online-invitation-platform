@echo off
setlocal
for /L %%I in (1,1,3) do (python release_check.py > V21_1_RELEASE_WINDOWS_%%I.log 2>&1 || exit /b 1)

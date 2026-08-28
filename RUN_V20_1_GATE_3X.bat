@echo off
setlocal
for /L %%I in (1,1,3) do (
  py -3 release_check.py > V20_1_RELEASE_WINDOWS_FINAL_%%I.txt 2>&1
  if errorlevel 1 type V20_1_RELEASE_WINDOWS_FINAL_%%I.txt & exit /b 1
  type V20_1_RELEASE_WINDOWS_FINAL_%%I.txt
)
endlocal

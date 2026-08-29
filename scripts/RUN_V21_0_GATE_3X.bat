@echo off
setlocal
for /L %%I in (1,1,3) do (
  py -3 release_check.py > V21_0_RELEASE_WINDOWS_FINAL_%%I.txt 2>&1
  if errorlevel 1 type V21_0_RELEASE_WINDOWS_FINAL_%%I.txt & exit /b 1
  findstr /C:"EINVITATION_V21_0_ALL_REQUIRED_REVIEW_CHECKS_PASSED" V21_0_RELEASE_WINDOWS_FINAL_%%I.txt >nul || exit /b 1
  findstr /C:"EINVITATION_V21_0_RELEASE_CHECK_PASSED" V21_0_RELEASE_WINDOWS_FINAL_%%I.txt >nul || exit /b 1
  type V21_0_RELEASE_WINDOWS_FINAL_%%I.txt
)
endlocal

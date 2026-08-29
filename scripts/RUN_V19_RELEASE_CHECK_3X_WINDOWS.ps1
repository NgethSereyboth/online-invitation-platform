$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

for ($run = 1; $run -le 3; $run++) {
    $log = "V19_RELEASE_WINDOWS_FINAL_$run.txt"
    Write-Host "=== V19 Windows release run $run of 3 ==="
    & python release_check.py 2>&1 | Tee-Object -FilePath $log
    if ($LASTEXITCODE -ne 0) {
        Write-Error "V19 Windows release run $run failed. See $log"
        exit $LASTEXITCODE
    }
    $text = Get-Content $log -Raw
    if ($text -notmatch "EINVITATION_V19_ALL_REQUIRED_REVIEW_CHECKS_PASSED" -or $text -notmatch "EINVITATION_V19_RELEASE_CHECK_PASSED") {
        Write-Error "V19 success markers are missing from $log"
        exit 2
    }
}

Write-Host "EINVITATION_V19_WINDOWS_3X_RELEASE_CHECK_PASSED"

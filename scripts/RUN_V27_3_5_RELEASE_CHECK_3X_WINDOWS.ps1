$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

for ($run = 1; $run -le 3; $run++) {
    Write-Host "V27.3.5 release check run $run of 3" -ForegroundColor Cyan
    & $python "release_check.py"
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Error "V27.3.5 release check failed on run $run with exit code $exitCode."
        exit $exitCode
    }
}

Write-Host "EINVITATION_V27_3_5_WINDOWS_3X_RELEASE_CHECK_PASSED" -ForegroundColor Green
exit 0

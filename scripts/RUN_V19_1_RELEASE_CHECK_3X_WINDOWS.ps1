$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$reviewMarker = "EINVITATION_V19_1_ALL_REQUIRED_REVIEW_CHECKS_PASSED"
$releaseMarker = "EINVITATION_V19_1_RELEASE_CHECK_PASSED"

for ($run = 1; $run -le 3; $run++) {
    $log = "V19_1_RELEASE_WINDOWS_FINAL_$run.txt"
    Write-Host "=== V19.1 Windows release run $run of 3 ==="
    & python release_check.py 2>&1 | Tee-Object -FilePath $log
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Write-Error "V19.1 Windows release run $run failed with exit code $code. See $log"
        exit $code
    }
    $text = Get-Content $log -Raw
    if ($text -notmatch [regex]::Escape($reviewMarker) -or $text -notmatch [regex]::Escape($releaseMarker)) {
        Write-Error "V19.1 success markers are missing from $log"
        exit 2
    }
    $deterministic = ([regex]::Matches(($text -split "Running 23 required browser checks sequentially\.\.\.")[0], "(?m)^  PASS tests/")).Count
    $browserSection = ($text -split "Running 23 required browser checks sequentially\.\.\.", 2)
    if ($browserSection.Count -ne 2) {
        Write-Error "Browser phase marker is missing from $log"
        exit 3
    }
    $browser = ([regex]::Matches($browserSection[1], "(?m)^  PASS tests/")).Count
    if ($deterministic -ne 41 -or $browser -ne 23) {
        Write-Error "Unexpected pass counts in $log: deterministic=$deterministic browser=$browser"
        exit 4
    }
}

Write-Host "EINVITATION_V19_1_WINDOWS_3X_RELEASE_CHECK_PASSED"

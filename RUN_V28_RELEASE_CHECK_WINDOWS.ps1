$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:EINVITE_REQUIRE_BROWSER = '1'
$log = Join-Path $PSScriptRoot 'V28_RELEASE_CHECK_WINDOWS.log'
python release_check_v28.py 2>&1 | Tee-Object -FilePath $log
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not (Select-String -Path $log -Pattern '^EINVITATION_V28_RELEASE_CHECK_PASSED$' -Quiet)) { throw 'V28 release marker was not produced.' }
Write-Output 'EINVITATION_V28_WINDOWS_RELEASE_CHECK_PASSED'

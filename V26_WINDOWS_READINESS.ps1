[CmdletBinding()]
param([switch]$StartHealthCheck)
$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$results=New-Object System.Collections.Generic.List[object]
function Add-Result([string]$Name,[bool]$Ok,[string]$Detail){$results.Add([pscustomobject]@{Check=$Name;Status=if($Ok){'Ready'}else{'Action needed'};Detail=$Detail})}
$python=Join-Path $Root '.venv\Scripts\python.exe'
Add-Result 'Project environment' (Test-Path $python) (if(Test-Path $python){$python}else{'Run SETUP_EINVITE_COMPLETE.bat'})
$browserCandidates=@("$env:ProgramFiles\Google\Chrome\Application\chrome.exe","${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe","$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe","${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe")
$browser=$browserCandidates|Where-Object{Test-Path $_}|Select-Object -First 1
Add-Result 'Chromium browser' ([bool]$browser) ($(if($browser){$browser}else{'Install Google Chrome or Microsoft Edge'}))
try{$test=Join-Path $Root 'data\.v26-write-test';New-Item -ItemType Directory -Force -Path (Split-Path $test)|Out-Null;Set-Content $test 'ok';Remove-Item $test -Force;Add-Result 'Data write permission' $true (Join-Path $Root 'data')}catch{Add-Result 'Data write permission' $false $_.Exception.Message}
$portBusy=$false
try{$portBusy=[bool](Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue)}catch{}
Add-Result 'Local port 8080' (-not $portBusy) ($(if($portBusy){'Already in use; stop the existing server or choose another port'}else{'Available'}))
if(Test-Path $python){
 try{& $python dependency_preflight.py|Out-Host;Add-Result 'Python dependencies' ($LASTEXITCODE -eq 0) 'dependency_preflight.py'}catch{Add-Result 'Python dependencies' $false $_.Exception.Message}
}
if($StartHealthCheck -and (Test-Path $python) -and -not $portBusy){
 $env:EINVITE_DATA_DIR=Join-Path $Root 'data';$env:EINVITE_COOKIE_SECURE='0';$env:EINVITE_DEV_AUTH_TOKENS='1'
 $proc=Start-Process -FilePath $python -ArgumentList @('-u','server.py','--host','127.0.0.1','--port','8080') -WorkingDirectory $Root -PassThru -WindowStyle Hidden
 try{$ok=$false;for($i=0;$i -lt 40;$i++){Start-Sleep -Milliseconds 250;try{$r=Invoke-RestMethod 'http://127.0.0.1:8080/api/health' -TimeoutSec 2;if($r.ok){$ok=$true;break}}catch{}};Add-Result 'Application health endpoint' $ok ($(if($ok){'http://127.0.0.1:8080/api/health'}else{'Server did not become ready'}))}finally{if(-not $proc.HasExited){Stop-Process -Id $proc.Id -Force}}
}
$results|Format-Table -AutoSize
$failed=@($results|Where-Object Status -ne 'Ready')
if($failed.Count){Write-Host "`nV26 Windows readiness needs attention in $($failed.Count) area(s)." -ForegroundColor Yellow;exit 1}
Write-Host "`nV26 Windows readiness passed." -ForegroundColor Green

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][string]$EnvironmentFile,
    [Parameter(Mandatory = $true)][string]$Domain,
    [ValidateRange(1024, 65535)][int]$BackendPort = 8080
)

$ErrorActionPreference = 'Stop'

function Import-DotEnv([string]$Path) {
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
        if ($trimmed -notmatch '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            throw "Invalid dotenv line in $Path"
        }
        $name = $Matches[1]
        $value = $Matches[2].Trim()
        if ($value.Length -ge 2 -and (($value[0] -eq '"' -and $value[-1] -eq '"') -or ($value[0] -eq "'" -and $value[-1] -eq "'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        Set-Item -Path "Env:$name" -Value $value
    }
}

$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$envFile = (Resolve-Path -LiteralPath $EnvironmentFile).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Virtual-environment Python is missing: $python" }

Import-DotEnv $envFile
$env:EINVITE_DATA_DIR = Join-Path $root 'data'
$env:EINVITE_ALLOWED_HOSTS = "$Domain,localhost,127.0.0.1"
$env:EINVITE_TRUSTED_PROXY_IPS = '127.0.0.1,::1'
$env:EINVITE_PUBLIC_BASE_URL = "https://$Domain"
$env:EINVITE_COOKIE_SECURE = '1'
$env:EINVITE_MALWARE_SCANNER_MODE = 'windows-defender'
$env:EINVITE_REQUIRE_MALWARE_SCAN = '1'
$env:HOST = '127.0.0.1'
$env:PORT = "$BackendPort"
$env:PYTHONUTF8 = '1'
$env:PYTHONUNBUFFERED = '1'

Set-Location -LiteralPath $root
& $python -u server.py --host 127.0.0.1 --port $BackendPort
exit $LASTEXITCODE

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][string]$CaddyExe,
    [Parameter(Mandatory = $true)][string]$Domain,
    [ValidateRange(1024, 65535)][int]$BackendPort = 8080
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$caddy = (Resolve-Path -LiteralPath $CaddyExe).Path
$config = Join-Path $root 'deploy\windows\Caddyfile'
$logs = Join-Path $root 'data\logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

$env:EINVITE_DOMAIN = $Domain
$env:EINVITE_BACKEND_PORT = "$BackendPort"
$env:EINVITE_CADDY_LOG = (Join-Path $logs 'caddy-access.json').Replace('\', '/')

Set-Location -LiteralPath $root
& $caddy run --config $config --adapter caddyfile
exit $LASTEXITCODE

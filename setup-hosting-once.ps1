[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Validate', 'Local', 'Network', 'Docker', 'WindowsServer')]
    [string]$Mode,
    [string]$Domain = '',
    [string]$EnvironmentFile = '.env.production',
    [string]$CaddyExe = '',
    [ValidateRange(1024, 65535)][int]$Port = 8080,
    [switch]$AllowPublicFirewall,
    [switch]$NoStart
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvironmentPath = if ([IO.Path]::IsPathRooted($EnvironmentFile)) { $EnvironmentFile } else { Join-Path $ProjectRoot $EnvironmentFile }

function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code ${LASTEXITCODE}: $Program" }
}

function Resolve-Python {
    $venv = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $venv -PathType Leaf) { return $venv }
    foreach ($name in @('python', 'py')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $command) { continue }
        try {
            & $command.Source -c "import sys; assert sys.version_info >= (3, 10)" 2>$null
            if ($LASTEXITCODE -eq 0) { return $command.Source }
        } catch {}
    }
    throw 'Python 3.10 or newer was not found. Run FIRST_TIME_SETUP.cmd first.'
}

function Assert-Domain([string]$Value) {
    if ($Value -notmatch '^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$') {
        throw '-Domain must be a hostname such as invite.example.com.'
    }
}

function Ensure-Environment([string]$ProxyIps, [switch]$StopAfterCreate) {
    if (Test-Path -LiteralPath $EnvironmentPath -PathType Leaf) { return }
    Assert-Domain $Domain
    $python = Resolve-Python
    Invoke-Checked $python @(
        (Join-Path $ProjectRoot 'prepare_production_env.py'),
        '--public-url', "https://$Domain",
        '--output', $EnvironmentPath,
        '--trusted-proxy-ips', $ProxyIps
    )
    if ($StopAfterCreate) {
        throw "A protected production environment was created at $EnvironmentPath. Replace its Docker-only postgres, redis, minio, backup, SMTP, and optional billing endpoints with your real Windows Server providers, then rerun this command."
    }
}

Set-Location -LiteralPath $ProjectRoot
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'server.py'))) {
    throw 'The hosting setup must remain inside the complete project folder.'
}

switch ($Mode) {
    'Validate' {
        Invoke-Checked 'powershell.exe' @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $ProjectRoot 'deploy-einvite-server.ps1'), '-Target', 'ValidateFiles')
    }
    'Local' {
        Invoke-Checked 'powershell.exe' @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $ProjectRoot 'setup-einvite-complete.ps1'), '-SkipDocker', '-SkipBrowserTests', '-NoAutoStart')
        $arguments = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $ProjectRoot 'host-einvite-laptop.ps1'), '-Port', "$Port", '-LocalOnly')
        if ($NoStart) { $arguments += '-CheckOnly' }
        Invoke-Checked 'powershell.exe' $arguments
    }
    'Network' {
        Invoke-Checked 'powershell.exe' @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $ProjectRoot 'setup-einvite-complete.ps1'), '-SkipDocker', '-SkipBrowserTests', '-NoAutoStart')
        $arguments = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $ProjectRoot 'host-einvite-laptop.ps1'), '-Port', "$Port")
        if ($NoStart) { $arguments += '-CheckOnly' }
        Invoke-Checked 'powershell.exe' $arguments
    }
    'Docker' {
        Assert-Domain $Domain
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
            throw 'Docker with Compose v2 was not found. On Windows 10/11 run FIRST_TIME_SETUP.cmd without -SkipDocker, start Docker Desktop, and rerun. On a Linux server install Docker Engine and the Compose v2 plugin.'
        }
        Invoke-Checked 'docker' @('compose', 'version')
        Ensure-Environment -ProxyIps '172.31.52.10'
        $arguments = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $ProjectRoot 'deploy-einvite-server.ps1'), '-Target', 'DockerOnline', '-Domain', $Domain, '-EnvironmentFile', $EnvironmentPath)
        if ($NoStart) { $arguments += '-NoStart' }
        Invoke-Checked 'powershell.exe' $arguments
    }
    'WindowsServer' {
        Assert-Domain $Domain
        if (-not (Test-Path -LiteralPath $EnvironmentPath -PathType Leaf)) {
            Ensure-Environment -ProxyIps '127.0.0.1,::1' -StopAfterCreate
        }
        $arguments = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $ProjectRoot 'deploy-einvite-server.ps1'), '-Target', 'WindowsServer', '-Domain', $Domain, '-EnvironmentFile', $EnvironmentPath, '-BackendPort', "$Port")
        if ($CaddyExe) { $arguments += @('-CaddyExe', $CaddyExe) }
        if ($AllowPublicFirewall) { $arguments += '-AllowPublicFirewall' }
        if ($NoStart) { $arguments += '-NoStart' }
        Invoke-Checked 'powershell.exe' $arguments
    }
}

Write-Host "HOSTING_SETUP_FINISHED mode=$Mode" -ForegroundColor Green

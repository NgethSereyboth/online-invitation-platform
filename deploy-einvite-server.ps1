[CmdletBinding()]
param(
    [ValidateSet('ValidateFiles', 'DockerOnline', 'WindowsServer')]
    [string]$Target = 'ValidateFiles',
    [string]$EnvironmentFile = '.env.production',
    [string]$Domain = '',
    [ValidateRange(1024, 65535)]
    [int]$BackendPort = 8080,
    [string]$CaddyExe = '',
    [switch]$AllowPublicFirewall,
    [switch]$CheckOnly,
    [switch]$NoStart
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvironmentPath = if ([IO.Path]::IsPathRooted($EnvironmentFile)) { $EnvironmentFile } else { Join-Path $ProjectRoot $EnvironmentFile }

function Write-Step([string]$Message) {
    Write-Host "`n== $Message ==" -ForegroundColor Cyan
}

function Assert-File([string]$RelativePath) {
    $path = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required deployment file is missing: $RelativePath"
    }
}

function Assert-Domain([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -notmatch '^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$') {
        throw "-Domain must be a DNS hostname such as invite.example.com (without https:// or a path)."
    }
}

function Resolve-Python {
    $venvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $venvPython -PathType Leaf) { return $venvPython }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return $python.Source }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return $py.Source }
    throw 'Python 3 was not found. Install Python 3.10 or newer and retry.'
}

function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code ${LASTEXITCODE}: $Program" }
}

function Test-DeploymentFiles {
    $required = @(
        'Dockerfile.online',
        'docker-compose.production.example.yml',
        'deploy\docker-compose.online.yml',
        'deploy\Caddyfile',
        'deploy\clamd.remote.conf',
        'deploy\windows\Caddyfile',
        'deploy\windows\start-einvite-windows-server.ps1',
        'deploy\windows\start-einvite-caddy.ps1',
        'deploy\linux\einvite.service.template',
        'deploy\linux\Caddyfile.template',
        'deploy\linux\setup-einvite-linux-once.sh',
        'ONLINE_AND_SERVER_HOSTING.md',
        'FIRST_TIME_INSTALL_AND_HOSTING.md',
        'FIRST_TIME_SETUP.cmd',
        'FIRST_TIME_HOSTING_SETUP.cmd',
        'setup-hosting-once.ps1',
        'production_preflight.py'
    )
    foreach ($file in $required) { Assert-File $file }
    Write-Host 'MULTI_HOST_DEPLOYMENT_FILES_VALID' -ForegroundColor Green
}

function Test-ProductionEnvironment([switch]$Dependencies) {
    if (-not (Test-Path -LiteralPath $EnvironmentPath -PathType Leaf)) {
        throw "Production environment file not found: $EnvironmentPath. Generate it with prepare_production_env.py first."
    }
    $python = Resolve-Python
    $arguments = @((Join-Path $ProjectRoot 'production_preflight.py'), '--env-file', $EnvironmentPath)
    if ($Dependencies) { $arguments += '--check-dependencies' }
    Invoke-Checked $python $arguments
}

function Install-WindowsServer {
    Assert-Domain $Domain
    if ($CheckOnly) {
        Write-Host "WINDOWS_SERVER_PLAN_VALID domain=$Domain backend=127.0.0.1:$BackendPort" -ForegroundColor Green
        return
    }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Windows Server installation must be run from PowerShell as Administrator.'
    }

    Write-Step 'Preparing isolated Python runtime'
    $venvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $python = Resolve-Python
        Invoke-Checked $python @('-m', 'venv', (Join-Path $ProjectRoot '.venv'))
    }
    Invoke-Checked $venvPython @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', (Join-Path $ProjectRoot 'requirements-production.txt'))
    Test-ProductionEnvironment -Dependencies

    $dataPath = Join-Path $ProjectRoot 'data'
    New-Item -ItemType Directory -Force -Path (Join-Path $dataPath 'logs') | Out-Null

    Write-Step 'Registering restartable application startup task'
    $appLauncher = Join-Path $ProjectRoot 'deploy\windows\start-einvite-windows-server.ps1'
    $escapedRoot = $ProjectRoot.Replace('"', '""')
    $escapedEnv = $EnvironmentPath.Replace('"', '""')
    $appArguments = "-NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$appLauncher`" -ProjectRoot `"$escapedRoot`" -EnvironmentFile `"$escapedEnv`" -Domain `"$Domain`" -BackendPort $BackendPort"
    $appAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $appArguments -WorkingDirectory $ProjectRoot
    $startup = New-ScheduledTaskTrigger -AtStartup
    $system = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -RestartCount 20 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable
    Register-ScheduledTask -TaskName 'EInvite-Web' -Action $appAction -Trigger $startup -Principal $system -Settings $settings -Description 'E-Invitation production application' -Force | Out-Null

    if ($CaddyExe) {
        $resolvedCaddy = (Resolve-Path -LiteralPath $CaddyExe).Path
        Write-Step 'Registering Caddy HTTPS startup task'
        $caddyLauncher = Join-Path $ProjectRoot 'deploy\windows\start-einvite-caddy.ps1'
        $caddyConfig = Join-Path $ProjectRoot 'deploy\windows\Caddyfile'
        $env:EINVITE_DOMAIN = $Domain
        $env:EINVITE_BACKEND_PORT = "$BackendPort"
        $env:EINVITE_CADDY_LOG = (Join-Path $dataPath 'logs\caddy-access.json').Replace('\', '/')
        Invoke-Checked $resolvedCaddy @('validate', '--config', $caddyConfig, '--adapter', 'caddyfile')
        $caddyArguments = "-NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$caddyLauncher`" -ProjectRoot `"$escapedRoot`" -CaddyExe `"$resolvedCaddy`" -Domain `"$Domain`" -BackendPort $BackendPort"
        $caddyAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $caddyArguments -WorkingDirectory $ProjectRoot
        Register-ScheduledTask -TaskName 'EInvite-Caddy' -Action $caddyAction -Trigger $startup -Principal $system -Settings $settings -Description 'E-Invitation HTTPS reverse proxy' -Force | Out-Null
        $firewallProfiles = if ($AllowPublicFirewall) { 'Domain,Private,Public' } else { 'Domain,Private' }
        foreach ($port in 80, 443) {
            $ruleName = "EInvite HTTPS $port"
            $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
            if ($existingRule) {
                Set-NetFirewallRule -DisplayName $ruleName -Enabled True -Action Allow -Profile $firewallProfiles | Out-Null
            } else {
                New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port -Profile $firewallProfiles | Out-Null
            }
        }
    } else {
        Write-Warning 'Caddy was not registered. Keep port 8080 private and terminate HTTPS with IIS, Caddy, or another trusted reverse proxy.'
    }

    if (-not $NoStart) {
        Start-ScheduledTask -TaskName 'EInvite-Web'
        if ($CaddyExe) { Start-ScheduledTask -TaskName 'EInvite-Caddy' }
    }
    Write-Host 'WINDOWS_SERVER_INSTALL_COMPLETE' -ForegroundColor Green
    Write-Host "Health check: https://$Domain/api/health/ready"
}

Test-DeploymentFiles
if ($Target -eq 'ValidateFiles') { exit 0 }

if ($Target -eq 'DockerOnline') {
    Assert-Domain $Domain
    Test-ProductionEnvironment
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) { throw 'Docker was not found. Install Docker Engine with Compose v2 and retry.' }
    $env:EINVITE_DOMAIN = $Domain
    $env:EINVITE_ENV_FILE = $EnvironmentPath
    Write-Step 'Validating the merged online container stack'
    $composeArguments = @('compose', '--env-file', $EnvironmentPath, '-f', (Join-Path $ProjectRoot 'docker-compose.production.example.yml'), '-f', (Join-Path $ProjectRoot 'deploy\docker-compose.online.yml'), 'config', '--quiet')
    Invoke-Checked $docker.Source $composeArguments
    if ($CheckOnly -or $NoStart) {
        Write-Host 'DOCKER_ONLINE_PLAN_VALID' -ForegroundColor Green
        exit 0
    }
    Write-Step 'Building and starting the online stack'
    $upArguments = @('compose', '--env-file', $EnvironmentPath, '-f', (Join-Path $ProjectRoot 'docker-compose.production.example.yml'), '-f', (Join-Path $ProjectRoot 'deploy\docker-compose.online.yml'), 'up', '-d', '--build')
    Invoke-Checked $docker.Source $upArguments
    Invoke-Checked $docker.Source @('compose', '--env-file', $EnvironmentPath, '-f', (Join-Path $ProjectRoot 'docker-compose.production.example.yml'), '-f', (Join-Path $ProjectRoot 'deploy\docker-compose.online.yml'), 'ps')
    Write-Host "DOCKER_ONLINE_DEPLOYMENT_COMPLETE https://$Domain" -ForegroundColor Green
    exit 0
}

if ($Target -eq 'WindowsServer') {
    Install-WindowsServer
    exit 0
}

[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)][int]$Port = 8080,
    [switch]$LocalOnly,
    [switch]$SkipFirewall,
    [switch]$SkipDependencyInstall,
    [switch]$NoBrowser,
    [switch]$AllowUploadsWithoutMalwareScan,
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Some terminals and automation tools can provide both "Path" and "PATH" in
# the inherited Windows environment. PowerShell's Start-Process treats those
# case-only variants as duplicate dictionary keys and refuses to launch. Keep
# one canonical process-level entry before we start Python, netsh, or a browser.
$inheritedPath = $env:Path
[Environment]::SetEnvironmentVariable('PATH', $null, 'Process')
[Environment]::SetEnvironmentVariable('Path', $inheritedPath, 'Process')

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ProjectRoot '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$DataDir = Join-Path $ProjectRoot 'data'
$Requirements = Join-Path $ProjectRoot 'requirements-production.txt'
$DependencyMarker = Join-Path $DataDir '.laptop-host-dependencies.sha256'
$FirewallRule = "E-invitation Laptop Host TCP $Port"

function Write-Step([string]$Message) {
    Write-Host ''
    Write-Host ('=' * 68) -ForegroundColor DarkGray
    Write-Host $Message -ForegroundColor Cyan
    Write-Host ('=' * 68) -ForegroundColor DarkGray
}

function Find-Python {
    if (Test-Path -LiteralPath $VenvPython) {
        return @{ Command = $VenvPython; Prefix = @() }
    }
    foreach ($candidate in @(
        @{ Command = 'py'; Prefix = @('-3') },
        @{ Command = 'python'; Prefix = @() },
        @{ Command = 'python3'; Prefix = @() }
    )) {
        if (-not (Get-Command $candidate.Command -ErrorAction SilentlyContinue)) { continue }
        try {
            & $candidate.Command @($candidate.Prefix) -c 'import sys; assert sys.version_info >= (3, 10)' 2>$null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        } catch {}
    }
    $localPythonRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
    if (Test-Path -LiteralPath $localPythonRoot) {
        $executables = Get-ChildItem -LiteralPath $localPythonRoot -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName 'python.exe' } |
            Where-Object { Test-Path -LiteralPath $_ }
        foreach ($executable in $executables) {
            try {
                & $executable -c 'import sys; assert sys.version_info >= (3, 10)' 2>$null
                if ($LASTEXITCODE -eq 0) { return @{ Command = $executable; Prefix = @() } }
            } catch {}
        }
    }
    return $null
}

function Install-PythonIfMissing {
    if (-not (Get-Command 'winget' -ErrorAction SilentlyContinue)) {
        throw 'Python 3.10 or newer and Windows Package Manager were not found. Install Python from python.org, then run this launcher again.'
    }
    Write-Host 'Python was not found. Installing Python 3.13 for the current Windows user...' -ForegroundColor Yellow
    & winget install --id Python.Python.3.13 -e --scope user --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw "Python installation failed with winget exit code $LASTEXITCODE." }
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machinePath;$userPath"
    $python = Find-Python
    if (-not $python) { throw 'Python was installed but is not usable yet. Restart Windows and run this launcher again.' }
    return $python
}

function Invoke-Python([hashtable]$Launcher, [string[]]$Arguments) {
    & $Launcher.Command @($Launcher.Prefix) @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE."
    }
}

function Get-LanIPv4 {
    try {
        $routes = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction Stop |
            Sort-Object RouteMetric, InterfaceMetric
        foreach ($route in $routes) {
            $address = Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $route.InterfaceIndex -ErrorAction SilentlyContinue |
                Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
                Select-Object -First 1 -ExpandProperty IPAddress
            if ($address) { return $address }
        }
    } catch {}
    try {
        return Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.PrefixOrigin -ne 'WellKnown' } |
            Select-Object -First 1 -ExpandProperty IPAddress
    } catch { return $null }
}

function Test-PortAvailable([int]$Number) {
    try {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Number)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch { return $false }
}

function Ensure-PrivateFirewallRule {
    if ($LocalOnly -or $SkipFirewall) { return }
    try {
        if (Get-NetFirewallRule -DisplayName $FirewallRule -ErrorAction SilentlyContinue) {
            Write-Host 'Private-network firewall rule is ready.' -ForegroundColor Green
            return
        }
    } catch {}
    Write-Host 'Windows may request permission once to allow private-network access.' -ForegroundColor Yellow
    try {
        $arguments = "advfirewall firewall add rule name=`"$FirewallRule`" dir=in action=allow protocol=TCP localport=$Port profile=private"
        $process = Start-Process -FilePath 'netsh.exe' -Verb RunAs -ArgumentList $arguments -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw "netsh exited with code $($process.ExitCode)" }
        Write-Host 'Private-network firewall rule created.' -ForegroundColor Green
    } catch {
        Write-Warning "Firewall access was not configured: $($_.Exception.Message)"
        Write-Warning 'This laptop can still use the site, but other devices may be blocked until TCP access is allowed on the Private profile.'
    }
}

function Test-RequiredPythonModules {
    if (-not (Test-Path -LiteralPath $VenvPython)) { return $false }
    & $VenvPython -c 'import PIL,qrcode,argon2,cryptography,fontTools,brotli' 2>$null
    return $LASTEXITCODE -eq 0
}

function Find-WindowsDefenderCli {
    $candidates = @()
    $platformRoot = Join-Path $env:ProgramData 'Microsoft\Windows Defender\Platform'
    if (Test-Path -LiteralPath $platformRoot) {
        $candidates += Get-ChildItem -LiteralPath $platformRoot -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName 'MpCmdRun.exe' }
    }
    $candidates += Join-Path $env:ProgramFiles 'Windows Defender\MpCmdRun.exe'
    return $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}

function Test-WindowsDefenderScanner([string]$Cli) {
    if (-not $Cli) { return $false }
    & $Cli -Scan -ScanType 3 -File (Join-Path $ProjectRoot 'LAPTOP_HOSTING.md') -DisableRemediation *> $null
    return $LASTEXITCODE -eq 0
}

try {
    Set-Location $ProjectRoot
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'server.py'))) {
        throw 'server.py is missing. Keep this launcher in the project root.'
    }
    if (-not (Test-Path -LiteralPath $Requirements)) {
        throw 'requirements-production.txt is missing.'
    }

    $systemPython = Find-Python
    if (-not $systemPython -and -not $CheckOnly) { $systemPython = Install-PythonIfMissing }
    if (-not $systemPython) { throw 'Python 3.10 or newer was not found.' }
    $lanAddress = if ($LocalOnly) { $null } else { Get-LanIPv4 }
    $bindHost = if ($LocalOnly -or -not $lanAddress) { '127.0.0.1' } else { '0.0.0.0' }
    $localUrl = "http://127.0.0.1:$Port"
    $publicUrl = if ($lanAddress -and -not $LocalOnly) { "http://${lanAddress}:$Port" } else { $localUrl }
    $defenderCli = Find-WindowsDefenderCli
    $defenderReady = $defenderCli -and (Test-WindowsDefenderScanner $defenderCli)
    if (-not $defenderReady -and -not $AllowUploadsWithoutMalwareScan) {
        throw 'Microsoft Defender could not complete an upload-scan test. Enable Windows Security, or explicitly use -AllowUploadsWithoutMalwareScan if another security product actively protects this laptop.'
    }

    if ($CheckOnly) {
        Write-Host 'LAPTOP_HOST_CHECK_PASSED' -ForegroundColor Green
        Write-Host "Python: $($systemPython.Command)"
        Write-Host "Local URL: $localUrl"
        Write-Host "Upload malware scanning: $(if ($defenderReady) { 'Microsoft Defender ready' } else { 'explicitly bypassed' })"
        if ($lanAddress -and -not $LocalOnly) { Write-Host "Private-network URL: $publicUrl" }
        exit 0
    }

    Write-Step '1/5 - Preparing the isolated laptop environment'
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        Write-Host 'Creating .venv for this laptop...'
        Invoke-Python $systemPython @('-m', 'venv', $VenvDir)
    }
    if (-not (Test-Path -LiteralPath $VenvPython)) { throw 'The .venv environment could not be created.' }

    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $DataDir 'uploads') -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $DataDir 'backups') -Force | Out-Null
    $requirementsHash = (Get-FileHash -LiteralPath $Requirements -Algorithm SHA256).Hash.ToLowerInvariant()
    $installedHash = if (Test-Path -LiteralPath $DependencyMarker) { (Get-Content -Raw -LiteralPath $DependencyMarker).Trim() } else { '' }
    $dependenciesReady = ($installedHash -eq $requirementsHash) -and (Test-RequiredPythonModules)
    if (-not $dependenciesReady) {
        if ($SkipDependencyInstall) { throw 'Required laptop-host dependencies are missing and -SkipDependencyInstall was selected.' }
        Write-Host 'Installing the pinned production dependencies. The first run may take several minutes...' -ForegroundColor Yellow
        & $VenvPython -m pip install --disable-pip-version-check -r $Requirements
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the internet connection and run this launcher again.' }
        if (-not (Test-RequiredPythonModules)) { throw 'The required image, QR, security, and font modules did not pass their import check.' }
        [IO.File]::WriteAllText($DependencyMarker, $requirementsHash + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
    } else {
        Write-Host 'Laptop dependencies are already current.' -ForegroundColor Green
    }

    Write-Step '2/5 - Preparing persistent local storage and security'
    $env:EINVITE_DATA_DIR = $DataDir
    $env:EINVITE_PUBLIC_BASE_URL = $publicUrl
    $env:EINVITE_COOKIE_SECURE = '0'
    $env:EINVITE_DEV_AUTH_TOKENS = '0'
    $env:EINVITE_ENFORCE_PLAN_LIMITS = '0'
    $env:EINVITE_PRODUCTION = '0'
    $env:EINVITE_REQUIRE_DURABLE_SERVICES = '0'
    $env:EINVITE_DATABASE_URL = ''
    $env:EINVITE_REDIS_URL = ''
    $env:EINVITE_OBJECT_STORAGE_PROVIDER = 'local'
    $env:EINVITE_MALWARE_SCANNER_MODE = if ($defenderReady) { 'windows-defender' } else { '' }
    $env:EINVITE_REQUIRE_MALWARE_SCAN = if ($AllowUploadsWithoutMalwareScan) { '0' } else { '1' }
    $env:EINVITE_REQUEST_SOCKET_TIMEOUT_SECONDS = '30'
    $env:EINVITE_MAX_CONCURRENT_REQUESTS = '32'
    $allowedHosts = @('127.0.0.1', 'localhost', $env:COMPUTERNAME, $lanAddress) |
        Where-Object { $_ } | ForEach-Object { $_.ToString().Trim().ToLowerInvariant() } | Select-Object -Unique
    $env:EINVITE_ALLOWED_HOSTS = $allowedHosts -join ','
    Write-Host "Persistent data: $DataDir"
    Write-Host 'SQLite, uploads, generated signing secrets, and backups stay on this laptop.' -ForegroundColor Green
    if ($defenderReady) { Write-Host 'Every uploaded material will be quarantined and scanned by Microsoft Defender before storage.' -ForegroundColor Green }

    Write-Step '3/5 - Configuring private-network access'
    if (-not $lanAddress -and -not $LocalOnly) {
        Write-Warning 'No private-network IPv4 address was found. Starting in this-laptop-only mode.'
    }
    Ensure-PrivateFirewallRule
    if (-not (Test-PortAvailable $Port)) {
        throw "TCP port $Port is already in use. Close the existing server or run: HOST_EINVITE_ON_LAPTOP.bat -Port 8081"
    }

    Write-Step '4/5 - Starting and verifying the website'
    Write-Host "This laptop: $localUrl" -ForegroundColor Green
    if ($lanAddress -and -not $LocalOnly) {
        Write-Host "Other devices on the same private Wi-Fi/LAN: $publicUrl" -ForegroundColor Green
    }
    Write-Host ''
    Write-Host 'This mode is private-network HTTP hosting, not public Internet hosting.' -ForegroundColor Yellow
    Write-Host 'Keep the laptop awake and this window open. Press Ctrl+C to stop.' -ForegroundColor Yellow
    Write-Host ''

    $server = Start-Process -FilePath $VenvPython -ArgumentList @('-u', 'server.py', '--host', $bindHost, '--port', "$Port") -WorkingDirectory $ProjectRoot -NoNewWindow -PassThru
    try {
        $deadline = (Get-Date).AddSeconds(45)
        $healthy = $false
        do {
            if ($server.HasExited) { throw "The server exited before becoming ready (code $($server.ExitCode))." }
            $health = $null
            try {
                $health = Invoke-RestMethod -Uri "$localUrl/api/health" -TimeoutSec 2
            } catch {}
            if ($health -and $health.ok -eq $true -and $health.dependencies.malwareScanRequired -eq $true -and $health.dependencies.malwareScanReady -ne $true) {
                throw 'The server could not activate required upload malware scanning.'
            }
            if ($health -and $health.ok -eq $true -and $health.dependencies.qrReady -eq $true -and ($AllowUploadsWithoutMalwareScan -or $health.dependencies.malwareScanReady -eq $true)) { $healthy = $true; break }
            Start-Sleep -Milliseconds 700
        } while ((Get-Date) -lt $deadline)
        if (-not $healthy) { throw 'The server did not pass its health check within 45 seconds.' }

        Write-Step '5/5 - Laptop host is ready'
        Write-Host 'Health check passed. The website is ready.' -ForegroundColor Green
        if (-not $NoBrowser) { Start-Process $localUrl }
        Wait-Process -Id $server.Id
        exit $server.ExitCode
    } finally {
        if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
    }
} catch {
    Write-Host ''
    Write-Host "LAPTOP HOST ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

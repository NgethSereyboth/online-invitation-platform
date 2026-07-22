[CmdletBinding()]
param(
    [switch]$SkipDocker,
    [switch]$SkipBrowserTests,
    [switch]$NoAutoStart
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile = Join-Path $ProjectRoot 'setup-einvite.log'
$VenvDir = Join-Path $ProjectRoot '.venv'
$script:NeedsRestart = $false

function Write-Log {
    param([string]$Message, [ConsoleColor]$Color = [ConsoleColor]::Gray)
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$timestamp] $Message"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $Message -ForegroundColor $Color
}

function Write-Step {
    param([string]$Message)
    Write-Host ''
    Write-Host ('=' * 72) -ForegroundColor DarkGray
    Write-Log $Message Cyan
    Write-Host ('=' * 72) -ForegroundColor DarkGray
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine;$user"
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Ensure-Winget {
    if (Test-Command 'winget') { return }
    throw @'
Windows Package Manager (winget) was not found.
Install or update "App Installer" from the Microsoft Store, then run this setup again.
On current Windows 10/11 systems winget is normally included with App Installer.
'@
}

function Test-WingetPackage {
    param([string]$Id)
    try {
        $output = & winget list --id $Id -e --accept-source-agreements 2>$null | Out-String
        return $output -match [regex]::Escape($Id)
    } catch {
        return $false
    }
}

function Install-WingetPackage {
    param(
        [string]$Id,
        [string]$DisplayName,
        [switch]$Optional
    )
    if (Test-WingetPackage $Id) {
        Write-Log "$DisplayName is already installed." Green
        return $true
    }

    Write-Log "Installing $DisplayName..." Yellow
    & winget install --id $Id -e --silent --accept-package-agreements --accept-source-agreements --disable-interactivity | Out-Host
    $code = $LASTEXITCODE
    Refresh-Path

    if ($code -eq 0 -or (Test-WingetPackage $Id)) {
        Write-Log "$DisplayName installed." Green
        return $true
    }

    if ($Optional) {
        Write-Log "Optional component $DisplayName could not be installed automatically. Continuing." Yellow
        return $false
    }
    throw "Failed to install required component: $DisplayName ($Id). winget exit code: $code"
}

function Test-PythonExecutable {
    param(
        [string]$Command,
        [string[]]$PrefixArgs = @()
    )
    try {
        $global:LASTEXITCODE = 0
        $output = & $Command @PrefixArgs -c "import sys; print(sys.executable)" 2>$null
        $code = $LASTEXITCODE
        if ($code -ne 0) { return $null }
        $exe = ($output | Select-Object -Last 1 | ForEach-Object { $_.ToString().Trim() })
        if (-not $exe) { return $null }
        # Microsoft Store App Execution Aliases can exist without a usable Python.
        # A real interpreter must both exit successfully and report an executable path.
        return @{ Command = $Command; Args = @($PrefixArgs); Executable = $exe }
    } catch {
        return $null
    }
}

function Find-PythonLauncher {
    Refresh-Path

    # First try commands that may already be on PATH. Do not trust Get-Command alone:
    # Windows can expose a broken Store alias that returns exit code 9009.
    foreach ($candidate in @(
        @{ Command = 'py'; Args = @('-3') },
        @{ Command = 'python'; Args = @() },
        @{ Command = 'python3'; Args = @() }
    )) {
        if (Test-Command $candidate.Command) {
            $working = Test-PythonExecutable -Command $candidate.Command -PrefixArgs $candidate.Args
            if ($working) { return $working }
        }
    }

    # Python can be installed correctly but not yet visible in the current elevated PATH.
    $knownRoots = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python'),
        $env:ProgramFiles,
        ${env:ProgramFiles(x86)}
    ) | Where-Object { $_ -and (Test-Path $_) }

    $directCandidates = New-Object System.Collections.Generic.List[string]
    $localPythonRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
    if (Test-Path $localPythonRoot) {
        Get-ChildItem $localPythonRoot -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object {
                $exe = Join-Path $_.FullName 'python.exe'
                if (Test-Path $exe) { $directCandidates.Add($exe) }
            }
    }
    foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not $base -or -not (Test-Path $base)) { continue }
        Get-ChildItem $base -Directory -Filter 'Python*' -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object {
                $exe = Join-Path $_.FullName 'python.exe'
                if (Test-Path $exe) { $directCandidates.Add($exe) }
            }
    }

    foreach ($exe in ($directCandidates | Select-Object -Unique)) {
        $working = Test-PythonExecutable -Command $exe
        if ($working) { return $working }
    }
    return $null
}

function Invoke-PythonLauncher {
    param(
        [hashtable]$Launcher,
        [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments
    )
    $command = [string]$Launcher.Command
    $allArgs = @($Launcher.Args) + @($Arguments)
    $global:LASTEXITCODE = 0
    & $command @allArgs
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        throw "Python command failed with exit code $code. Command: $command $($allArgs -join ' ')"
    }
}

function New-DesktopShortcut {
    param(
        [string]$Name,
        [string]$Target,
        [string]$Arguments = '',
        [string]$Description = ''
    )
    try {
        $desktop = [Environment]::GetFolderPath('Desktop')
        $shortcutPath = Join-Path $desktop "$Name.lnk"
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $Target
        $shortcut.Arguments = $Arguments
        $shortcut.WorkingDirectory = $ProjectRoot
        $shortcut.Description = $Description
        $shortcut.Save()
        Write-Log "Created desktop shortcut: $Name" DarkGreen
    } catch {
        Write-Log "Could not create desktop shortcut '$Name': $($_.Exception.Message)" Yellow
    }
}

function Add-FirewallRule {
    try {
        $ruleName = 'E-invitation-website Local Server 8080'
        $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
        if (-not $existing) {
            New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080 -Profile Private | Out-Null
            Write-Log 'Added Windows Firewall rule for private-network access on port 8080.' Green
        } else {
            Write-Log 'Windows Firewall rule for port 8080 already exists.' Green
        }
    } catch {
        Write-Log "Could not automatically create the firewall rule: $($_.Exception.Message)" Yellow
    }
}

function Start-LocalServerAndBrowser {
    $runner = Join-Path $ProjectRoot 'RUN_EINVITE_LOCAL.bat'
    if (Test-Path $runner) {
        Write-Log 'Starting the local E-invitation server...' Cyan
        Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', ('"' + $runner + '"') -WorkingDirectory $ProjectRoot
    }
}

try {
    Set-Location $ProjectRoot
    Set-Content -Path $LogFile -Value "E-invitation setup started $(Get-Date -Format o)" -Encoding UTF8

    if (-not (Test-Path (Join-Path $ProjectRoot 'server.py'))) {
        throw "server.py was not found. Keep these setup files inside the E-invitation-website project folder."
    }

    Write-Step '1/8 - Checking Windows package manager'
    Ensure-Winget
    Write-Log 'winget is available.' Green

    Write-Step '2/8 - Installing the Windows applications used by the project'
    $detectedPython = Find-PythonLauncher
    if (-not $detectedPython) {
        Write-Log 'No working Python interpreter was found. Installing Python 3.13...' Yellow
        $pythonReady = Install-WingetPackage -Id 'Python.Python.3.13' -DisplayName 'Python 3.13' -Optional
        Refresh-Path
        $detectedPython = Find-PythonLauncher
        if (-not $detectedPython) {
            Write-Log 'Python 3.13 is still not usable. Trying Python 3.12...' Yellow
            Install-WingetPackage -Id 'Python.Python.3.12' -DisplayName 'Python 3.12'
            Refresh-Path
            $detectedPython = Find-PythonLauncher
        }
    } else {
        Write-Log "Working Python detected: $($detectedPython.Executable)" Green
    }

    Install-WingetPackage -Id 'Git.Git' -DisplayName 'Git' -Optional | Out-Null
    Install-WingetPackage -Id 'OpenJS.NodeJS.LTS' -DisplayName 'Node.js LTS' -Optional | Out-Null
    Install-WingetPackage -Id 'Cloudflare.cloudflared' -DisplayName 'Cloudflare Tunnel (cloudflared)' -Optional | Out-Null

    if (-not $SkipDocker) {
        $dockerInstalled = Install-WingetPackage -Id 'Docker.DockerDesktop' -DisplayName 'Docker Desktop' -Optional
        if ($dockerInstalled) {
            Write-Log 'Docker Desktop was installed or is already present. First launch may require accepting terms, enabling virtualization/WSL, or restarting Windows.' Yellow
        }
    }

    Refresh-Path
    $python = if ($detectedPython) { $detectedPython } else { Find-PythonLauncher }
    if (-not $python) {
        throw 'Python is still unavailable after installation. Restart Windows, then run SETUP_EINVITE_COMPLETE.bat again.'
    }

    Write-Step '3/8 - Creating an isolated Python environment for this project'
    if (-not (Test-Path (Join-Path $VenvDir 'Scripts\python.exe'))) {
        Invoke-PythonLauncher $python '-m' 'venv' $VenvDir
        Write-Log 'Created .venv virtual environment.' Green
    } else {
        Write-Log '.venv already exists; reusing it.' Green
    }

    $VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
    if (-not (Test-Path $VenvPython)) { throw 'The project Python environment could not be created.' }

    Write-Step '4/8 - Installing project Python dependencies'
    & $VenvPython -m pip install --upgrade pip setuptools wheel
    if ($LASTEXITCODE -ne 0) { throw 'Failed to update pip.' }

    if (Test-Path 'requirements-production.txt') {
        & $VenvPython -m pip install -r requirements-production.txt
        if ($LASTEXITCODE -ne 0) { throw 'Failed to install production Python dependencies.' }
        Write-Log 'Installed PostgreSQL, object-storage, and Redis integration libraries.' Green
    }

    if (-not $SkipBrowserTests -and (Test-Path 'requirements-test.txt')) {
        & $VenvPython -m pip install -r requirements-test.txt
        if ($LASTEXITCODE -ne 0) { throw 'Failed to install browser test dependencies.' }
        Write-Log 'Installed Playwright and image-test dependencies.' Green

        Write-Log 'Downloading the Playwright Chromium browser used by the review tests...' Yellow
        & $VenvPython -m playwright install chromium
        if ($LASTEXITCODE -ne 0) {
            Write-Log 'Playwright Chromium could not be downloaded. The application can still run normally; only automated browser screenshots may be unavailable.' Yellow
        } else {
            Write-Log 'Playwright Chromium installed.' Green
        }
    }

    Write-Step '5/8 - Preparing local runtime folders and configuration'
    New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot 'data') | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot 'data\uploads') | Out-Null

    $localEnv = @"
# Local Windows runtime settings generated by SETUP_EINVITE_COMPLETE.bat
# The run scripts set these values automatically; this file is a reference.
HOST=127.0.0.1
PORT=8080
EINVITE_DATA_DIR=$($ProjectRoot.Replace('\','/'))/data
EINVITE_PUBLIC_BASE_URL=http://127.0.0.1:8080
EINVITE_COOKIE_SECURE=0
EINVITE_DEV_AUTH_TOKENS=1
EINVITE_ENFORCE_PLAN_LIMITS=0
"@
    Set-Content -Path (Join-Path $ProjectRoot '.env.local.windows') -Value $localEnv -Encoding UTF8
    Write-Log 'Created local data folders and .env.local.windows reference file.' Green

    Write-Step '6/8 - Preparing local hosting tools'
    Add-FirewallRule

    Write-Step '7/8 - Creating desktop shortcuts'
    New-DesktopShortcut -Name 'E-invitation - Run Local' -Target (Join-Path $ProjectRoot 'RUN_EINVITE_LOCAL.bat') -Description 'Start E-invitation-website on this computer.'
    New-DesktopShortcut -Name 'E-invitation - Public Tunnel' -Target (Join-Path $ProjectRoot 'RUN_EINVITE_PUBLIC_TUNNEL.bat') -Description 'Start the local app and expose a temporary Cloudflare HTTPS URL.'
    New-DesktopShortcut -Name 'E-invitation - Review Tests' -Target (Join-Path $ProjectRoot 'RUN_EINVITE_REVIEW_TESTS.bat') -Description 'Run the project review/test suite.'

    Write-Step '8/8 - Final verification'
    & $VenvPython -m py_compile server.py
    if ($LASTEXITCODE -ne 0) { throw 'server.py did not pass Python compilation.' }
    Write-Log 'server.py compilation check passed.' Green

    $marker = @{
        InstalledAt = (Get-Date).ToString('o')
        ProjectRoot = $ProjectRoot
        Python = (& $VenvPython --version 2>&1 | Out-String).Trim()
        DockerRequested = (-not $SkipDocker)
        BrowserTestsRequested = (-not $SkipBrowserTests)
    } | ConvertTo-Json -Depth 3
    Set-Content -Path (Join-Path $ProjectRoot '.einvite-setup-complete.json') -Value $marker -Encoding UTF8

    Write-Host ''
    Write-Log 'COMPLETE: E-invitation-website is ready to run.' Green
    Write-Host ''
    Write-Host 'Useful launchers in this folder:' -ForegroundColor Cyan
    Write-Host '  RUN_EINVITE_LOCAL.bat              - normal local use' -ForegroundColor White
    Write-Host '  RUN_EINVITE_ON_NETWORK.bat         - use from other devices on your Wi-Fi/LAN' -ForegroundColor White
    Write-Host '  RUN_EINVITE_PUBLIC_TUNNEL.bat      - temporary public HTTPS URL' -ForegroundColor White
    Write-Host '  RUN_EINVITE_FULL_DOCKER_STACK.bat  - PostgreSQL + Redis + app' -ForegroundColor White
    Write-Host '  RUN_EINVITE_REVIEW_TESTS.bat       - automated project checks' -ForegroundColor White
    Write-Host '  BACKUP_EINVITE_DATA.bat            - make a runtime backup' -ForegroundColor White
    Write-Host ''

    if (-not $NoAutoStart) {
        Start-LocalServerAndBrowser
    }
    exit 0
} catch {
    Write-Host ''
    Write-Log "SETUP ERROR: $($_.Exception.Message)" Red
    Write-Log "Details: $($_ | Out-String)" DarkRed
    exit 1
}

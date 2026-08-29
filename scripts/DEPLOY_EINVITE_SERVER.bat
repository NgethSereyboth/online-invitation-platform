@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" (
  echo E-Invitation multi-host deployment
  echo.
  echo Examples:
  echo   DEPLOY_EINVITE_SERVER.bat ValidateFiles
  echo   DEPLOY_EINVITE_SERVER.bat DockerOnline -Domain invite.example.com
  echo   DEPLOY_EINVITE_SERVER.bat WindowsServer -Domain invite.example.com -CaddyExe C:\Tools\caddy.exe
  echo.
  echo Create .env.production first with:
  echo   python prepare_production_env.py --public-url https://invite.example.com --trusted-proxy-ips 172.31.52.10
  exit /b 2
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy-einvite-server.ps1" -Target %*
exit /b %errorlevel%

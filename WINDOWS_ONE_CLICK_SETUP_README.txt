E-INvITATION-WEBSITE - WINDOWS ONE-CLICK SETUP
================================================

FOR A COMPUTER WITH NO PROGRAMMING TOOLS INSTALLED

1. Extract the complete project ZIP to a normal folder, for example:
   C:\E-invitation-website

2. Double-click:
   SETUP_EINVITE_COMPLETE.bat

3. Approve the Windows administrator/UAC prompt if it appears.

The setup automatically installs/configures the tools used by the project:

REQUIRED / NORMAL LOCAL USE
- Python 3
- Project virtual Python environment (.venv)
- Production integration Python packages

SUPPORT / REVIEW TOOLS
- Git
- Node.js LTS
- Playwright + Chromium browser for automated UI/review tests

PUBLIC TEST HOSTING
- Cloudflare cloudflared, which can provide a temporary HTTPS URL from your PC

PRODUCTION-LIKE LOCAL HOSTING
- Docker Desktop
- The included Docker Compose file automatically runs PostgreSQL + Redis + the app

AFTER SETUP
-----------
Double-click one of these launchers:

RUN_EINVITE_LOCAL.bat
  Normal single-computer mode. Uses SQLite/local media.
  Opens http://127.0.0.1:8080

RUN_EINVITE_ON_NETWORK.bat
  Makes the project accessible to other devices on your private Wi-Fi/LAN.

RUN_EINVITE_PUBLIC_TUNNEL.bat
  Starts the local server and creates a temporary public Cloudflare HTTPS URL.
  This is useful for testing. Do not treat a temporary tunnel as final production hosting.

RUN_EINVITE_FULL_DOCKER_STACK.bat
  Runs a production-like local stack with:
  - App
  - PostgreSQL 16
  - Redis 7
  Docker Desktop must be running.

RUN_EINVITE_REVIEW_TESTS.bat
  Runs the project's review/test suite.

BACKUP_EINVITE_DATA.bat
  Creates a runtime backup using the project's backup utility.

STOP_EINVITE_LOCAL_PROCESSES.bat
  Stops Python servers/tunnels launched from this project.

STOP_EINVITE_FULL_DOCKER_STACK.bat
  Stops the Docker app/PostgreSQL/Redis stack while preserving its Docker volumes.

IMPORTANT NOTES
---------------
- Docker Desktop may require virtualization/WSL and sometimes a Windows restart after its first installation.
- Local mode does NOT require Docker. Python + SQLite is enough.
- Real production hosting still requires your final domain/HTTPS and provider credentials for any services you choose to use (SMTP, R2/S3, AI, billing, etc.).
- The Cloudflare quick tunnel URL changes when the tunnel restarts.
- The setup is safe to run again; it reuses already-installed components and the existing .venv.

TROUBLESHOOTING
---------------
A setup log is written to:
  setup-einvite.log

If Windows says winget is missing, install/update "App Installer" from the Microsoft Store and run setup again.

OPTIONAL ALWAYS-ON LOCAL HOSTING
-------------------------------
INSTALL_EINVITE_AUTOSTART.bat
  Adds a Windows scheduled task that starts the local server when you sign in.

REMOVE_EINVITE_AUTOSTART.bat
  Removes the scheduled auto-start task.

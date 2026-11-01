# Start the E-Invitation Platform in VS Code

This guide is for running the complete platform locally on a Windows computer. The project needs its Python backend, so do not use the VS Code **Live Server** extension and do not open `index.html` directly.

## 1. Extract the project

1. Extract the complete ZIP to a normal folder, such as `C:\Projects\e-invitation-platform`.
2. Do not edit or run the project while it is still inside the ZIP.
3. Keep the project folder in a location where your Windows account can create files.

## 2. Open the correct folder in VS Code

1. Open Visual Studio Code.
2. Select **File > Open Folder**.
3. Select the extracted project folder.
4. Confirm that `server.py`, `FIRST_TIME_SETUP.cmd`, and `RUN_EINVITE_LOCAL.bat` are visible at the top level in Explorer.
5. If VS Code asks whether you trust the authors, select **Yes, I trust the authors** for your own project copy.

If those three files are inside another folder, close the current workspace and open that inner folder instead.

## 3. Complete the one-time setup

This step is required only on the first run, after moving to a new computer, or when the Python dependencies change.

1. Open **Terminal > New Terminal** in VS Code.
2. Confirm that the terminal path is the project folder.
3. Run:

```powershell
.\FIRST_TIME_SETUP.cmd
```

4. Approve the Windows administrator prompt if it appears.
5. Wait for `FIRST_TIME_SETUP_COMPLETE`.

The setup installs or configures Python, creates `.venv`, installs the required packages, and prepares the local data folders. It is safe to run again after a project update.

For the complete developer and automated-browser testing toolchain, use this larger setup instead:

```powershell
.\SETUP_EINVITE_COMPLETE.bat
```

Normal local use does not require Docker, Node.js, Playwright, or production credentials.

## 4. Start the platform

In the VS Code terminal, run:

```powershell
.\RUN_EINVITE_LOCAL.bat
```

Keep that terminal or launcher window open. The platform should open automatically at:

```text
http://127.0.0.1:8080
```

If the browser does not open automatically, copy that address into Chrome, Edge, or Firefox.

## 5. Start without the launcher (optional)

The included launcher is recommended because it sets the correct local-development options. If you need to start the backend manually from a VS Code PowerShell terminal, run:

```powershell
$env:EINVITE_DATA_DIR="$PWD\data"
$env:EINVITE_PUBLIC_BASE_URL="http://127.0.0.1:8080"
$env:EINVITE_COOKIE_SECURE="0"
$env:EINVITE_DEV_AUTH_TOKENS="1"
$env:EINVITE_ENFORCE_PLAN_LIMITS="0"
.\.venv\Scripts\python.exe -u server.py --host 127.0.0.1 --port 8080
```

Then open `http://127.0.0.1:8080`.

## 6. Stop and restart

- To stop the server, focus its terminal and press **Ctrl+C**.
- You can also run `STOP_EINVITE_LOCAL_PROCESSES.bat`.
- To start it again, run `RUN_EINVITE_LOCAL.bat`.
- Refresh the browser after changing HTML, CSS, or JavaScript.
- Restart the server after changing `server.py`, backend modules, or environment settings.

## 7. Your local data

Local accounts, invitations, uploads, and generated secrets are stored under the project's `data` folder. Do not delete that folder when it contains work you want to keep.

Before replacing or updating the project, create a backup with:

```powershell
.\BACKUP_EINVITE_DATA.bat
```

Do not commit `.env.production`, databases, signing secrets, private uploads, or backup archives to GitHub.

## 8. Common problems

### The browser says `ERR_EMPTY_RESPONSE` or the page does not load

The backend is not running or its terminal closed. Return to VS Code and run:

```powershell
.\RUN_EINVITE_LOCAL.bat
```

Wait until the terminal reports that it is listening, then refresh `http://127.0.0.1:8080`.

### `.venv\Scripts\python.exe` was not found

Run the one-time setup again:

```powershell
.\FIRST_TIME_SETUP.cmd
```

### Setup failed

Read `setup-einvite.log` in the project folder. If Windows reports that `winget` is unavailable, install or update **App Installer** from the Microsoft Store and rerun the setup.

### Port 8080 is already in use

Stop the other local server or run this project temporarily on port 4175:

```powershell
$env:EINVITE_DATA_DIR="$PWD\data"
$env:EINVITE_PUBLIC_BASE_URL="http://127.0.0.1:4175"
$env:EINVITE_COOKIE_SECURE="0"
$env:EINVITE_DEV_AUTH_TOKENS="1"
$env:EINVITE_ENFORCE_PLAN_LIMITS="0"
.\.venv\Scripts\python.exe -u server.py --host 127.0.0.1 --port 4175
```

Open `http://127.0.0.1:4175` for that session.

### The page opens but backend features do not work

Make sure you opened the HTTP address above. Opening `index.html` directly or using Live Server cannot provide accounts, uploads, RSVP storage, publishing, or AI/backend functions.

## 9. Optional private-network access

To open the platform from another device on the same trusted Wi-Fi network, stop the local launcher and run:

```powershell
.\RUN_EINVITE_ON_NETWORK.bat
```

Use the private-network address shown by the launcher. Do not expose the local development port directly to the public internet.

For permanent online hosting, follow `FIRST_TIME_INSTALL_AND_HOSTING.md` instead of this local VS Code guide.

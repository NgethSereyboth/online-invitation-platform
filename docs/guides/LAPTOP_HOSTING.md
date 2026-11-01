# One-command laptop hosting

Double-click `HOST_EINVITE_ON_LAPTOP.bat`. The launcher performs the complete laptop-hosting flow:

1. Finds Python 3.10 or newer—or installs Python 3.13 through Windows Package Manager when missing—and creates an isolated `.venv` when needed.
2. Installs pinned production dependencies on the first run or when they change.
3. Creates persistent local SQLite, upload, backup, and signing-secret storage under `data/`.
4. Requires Microsoft Defender and quarantines/scans every uploaded file before it enters storage.
5. Requests a Windows Firewall rule limited to the **Private** network profile.
6. Detects the laptop's private IPv4 address, starts the server, verifies `/api/health`, and opens the website.

The same laptop uses `http://127.0.0.1:8080`. Phones and computers on the same private Wi-Fi/LAN use the network URL printed by the launcher.

## Important operating notes

- Keep the launcher window open and prevent the laptop from sleeping while guests use the website.
- This is private-network HTTP hosting. It does not expose the laptop safely to the public Internet.
- Do not configure router port forwarding for this mode. Use the existing Cloudflare tunnel launcher for a temporary public test URL, or the hardened production deployment for a permanent public service.
- Back up `data/` regularly. `BACKUP_EINVITE_DATA.bat` remains available for local backups.
- The launcher disables development authentication tokens and persists generated signing secrets locally.
- Backend source, environment files, databases, backups, tests, logs, and signing secrets are denied by the web server even when their URLs are guessed.
- Keep Windows Security real-time protection and virus definitions current. The application scanner is an additional upload gate, not a replacement for operating-system updates and endpoint protection.

## Optional command-line switches

```powershell
HOST_EINVITE_ON_LAPTOP.bat -Port 8081
HOST_EINVITE_ON_LAPTOP.bat -LocalOnly
HOST_EINVITE_ON_LAPTOP.bat -NoBrowser
HOST_EINVITE_ON_LAPTOP.bat -SkipFirewall
```

`-LocalOnly` binds only to `127.0.0.1`. `-SkipDependencyInstall` is intended for offline use after dependencies have already been installed. `-CheckOnly` performs a read-only prerequisite and address check without starting the server.

`-AllowUploadsWithoutMalwareScan` is an emergency compatibility override for a laptop protected by another antivirus product. It weakens upload protection and should not be used merely to avoid enabling Microsoft Defender.

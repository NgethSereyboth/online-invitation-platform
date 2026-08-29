"""Create a consistent ZIP backup of the SQLite database and uploaded materials."""
from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
import time
import zipfile
from pathlib import Path



def platform_env(name, default=None):
    """Read the current EINVITE_* setting, with legacy SOVAN_* fallback."""
    legacy = name.replace("EINVITE_", "SOVAN_", 1)
    return os.environ.get(name, os.environ.get(legacy, default))

ROOT = Path(__file__).resolve().parent
DATA = Path(platform_env("EINVITE_DATA_DIR", str(ROOT / "data"))).expanduser().resolve()
DB = DATA / "invites.db"
UPLOADS = DATA / "uploads"


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up E-invitation-website runtime data.")
    parser.add_argument("--output", default=str(ROOT / "backups"), help="Backup output directory")
    args = parser.parse_args()
    output = Path(args.output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = output / f"e-invitation-website-backup-{stamp}.zip"

    with tempfile.TemporaryDirectory(prefix="e-invitation-website-backup-") as temp_dir:
        snapshot = Path(temp_dir) / "invites.db"
        if DB.exists():
            source = sqlite3.connect(DB)
            destination = sqlite3.connect(snapshot)
            try:
                source.backup(destination)
            finally:
                destination.close()
                source.close()
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            if snapshot.exists():
                archive.write(snapshot, "data/invites.db")
            if UPLOADS.exists():
                for path in UPLOADS.rglob("*"):
                    if path.is_file():
                        archive.write(path, Path("data/uploads") / path.relative_to(UPLOADS))
    print(target)


if __name__ == "__main__":
    main()

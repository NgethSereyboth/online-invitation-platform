#!/usr/bin/env bash
# Rotate the deployment's long-lived secrets in an env file (ROADMAP §4.7).
#
# Full procedure, downtime estimates and per-secret caveats:
#   docs/ops/SECRETS-ROTATION.md
#
# Usage:
#   scripts/rotate-secrets.sh [--env-file PATH] [--dry-run] [--print]
#                             [--field-encryption] [NAME ...]
#
# Defaults rotate the secrets this repo can generate itself:
#   EINVITE_SECRET_KEY, EINVITE_BILLING_WEBHOOK_SECRET, EINVITE_STRIPE_WEBHOOK_SECRET
#
# --field-encryption additionally rotates EINVITE_FIELD_ENCRYPTION_KEY the only
# safe way this build supports: the current value is moved to
# EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS and a new key becomes active. Old
# ciphertexts keep decrypting through the fallback; run the re-encryption pass
# the script prints, then remove the previous key. Refuses if the active key is
# not in the env file (e.g. it lives in the data directory's sidecar file).
#
# Nothing secret is printed unless --print is passed; output carries short
# SHA-256 fingerprints so an operator can match values across systems.
#
# Exit codes: 0 success · 1 error · 2 --field-encryption requested but the
# active key was not found in the env file (nothing was changed for it).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
  if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

exec "$PYTHON" - "$REPO_ROOT" "$@" <<'PY'
"""Rotation core for scripts/rotate-secrets.sh (embedded; see the header)."""
from __future__ import annotations

import argparse
import hashlib
import re
import secrets
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(sys.argv[1])
DEFAULT_ENV_FILE = ROOT / ".env"

GENERATED = ["EINVITE_SECRET_KEY", "EINVITE_BILLING_WEBHOOK_SECRET", "EINVITE_STRIPE_WEBHOOK_SECRET"]
FIELD_KEY = "EINVITE_FIELD_ENCRYPTION_KEY"
FIELD_PREVIOUS = FIELD_KEY + "_PREVIOUS"
PROVIDER_ISSUED = {
    "EINVITE_SMTP_PASSWORD": "your SMTP provider",
    "EINVITE_OBJECT_STORAGE_ACCESS_KEY": "your S3/R2 provider",
    "EINVITE_OBJECT_STORAGE_SECRET_KEY": "your S3/R2 provider",
    "EINVITE_STRIPE_SECRET_KEY": "the Stripe dashboard",
    "EINVITE_BILLING_API_KEY": "your billing provider",
}


def fingerprint(value: str | None) -> str:
    if not value:
        return "unset"
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def read_env(path: Path) -> dict:
    values = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$", line)
            if match:
                values.setdefault(match.group(1), match.group(2).strip())
    return values


def write_env(path: Path, updates: dict, removals=()) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    remaining = dict(updates)
    drop = set(removals)
    out = []
    for line in lines:
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$", line)
        if match and match.group(1) in drop:
            continue
        if match and match.group(1) in remaining:
            name = match.group(1)
            out.append(f"{name}={remaining.pop(name)}")
        else:
            out.append(line)
    for name, value in remaining.items():
        out.append(f"{name}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def generate(kind: str) -> str:
    if kind == "fernet":
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode("ascii")
    return secrets.token_urlsafe(48)


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print", dest="show_values", action="store_true", help="also print the new values (for a secret manager)")
    parser.add_argument("--field-encryption", action="store_true", help="rotate EINVITE_FIELD_ENCRYPTION_KEY via the previous-key window")
    parser.add_argument("names", nargs="*", help="extra generated secrets to rotate")
    args = parser.parse_args(sys.argv[2:])  # sys.argv[1] is the repo root the shell passed

    env_file = Path(args.env_file).expanduser().resolve()
    current = read_env(env_file)
    updates: dict[str, str] = {}
    removals: list[str] = []

    names = list(dict.fromkeys(GENERATED + list(args.names)))
    for name in names:
        if name in (FIELD_KEY, FIELD_PREVIOUS):
            print(f"  {name}: use --field-encryption for this key")
            continue
        new = generate("fernet" if name.endswith("_ENCRYPTION_KEY") else "token")
        updates[name] = new
        print(f"  {name}: {fingerprint(current.get(name))} -> {fingerprint(new)}")

    rc = 0
    if args.field_encryption:
        old = current.get(FIELD_KEY, "")
        if not old:
            print(
                f"  {FIELD_KEY}: not in {env_file} — refusing to overwrite the active key;\n"
                f"    no values were written. The active key may live in\n"
                f"    <data-dir>/.field-encryption-key. Copy it into {FIELD_PREVIOUS} first, or\n"
                f"    put the current value in {env_file}, then re-run.",
                file=sys.stderr,
            )
            rc = 2
        else:
            try:
                from cryptography.fernet import Fernet
                Fernet(old.strip().encode("ascii"))
            except Exception:
                print(f"  {FIELD_KEY}: value in {env_file} is not a valid Fernet key — not rotating it.", file=sys.stderr)
                rc = 1
            else:
                new = generate("fernet")
                updates[FIELD_KEY] = new
                updates[FIELD_PREVIOUS] = old.strip()
                print(f"  {FIELD_KEY}: {fingerprint(old)} -> {fingerprint(new)} (old kept as {FIELD_PREVIOUS})")
                python_hint = ".venv/bin/python" if (ROOT / ".venv" / "bin" / "python").exists() else "python3"
                print("    Next: run the re-encryption pass while both keys are set —")
                print(f"      {python_hint} scripts/migrate_encrypt_sensitive_fields.py --data-dir <data-dir> --reencrypt")
                print(f"    Then remove {FIELD_PREVIOUS} from {env_file} and restart.")

    for name, provider in PROVIDER_ISSUED.items():
        print(f"  {name}: rotate at {provider}, then update {env_file} (see docs/ops/SECRETS-ROTATION.md)")

    if rc or not updates:
        if not updates:
            print("nothing to write.")
        return rc

    if args.dry_run:
        print(f"dry-run: {env_file} not modified.")
        return rc

    if env_file.is_file():
        backup = env_file.with_name(env_file.name + f".bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(env_file, backup)
        try:
            backup.chmod(0o600)
        except OSError:
            pass
        print(f"backup: {backup}")
    write_env(env_file, updates, removals)
    print(f"wrote {len(updates)} value(s) to {env_file}")
    if args.show_values:
        for name in updates:
            print(f"PRINT {name}={updates[name]}")
    else:
        print("values not printed; re-run with --print if you must copy them into a secret manager.")
    print("restart the server to pick the new values up.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
PY

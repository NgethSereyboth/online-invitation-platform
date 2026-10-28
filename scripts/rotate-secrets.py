#!/usr/bin/env python3
"""Emit a rotated-secret candidate file for a deployment (ROADMAP §4.7, B-3).

This is the **host/secret-store** companion to ``scripts/rotate-secrets.sh``:

* ``rotate-secrets.sh`` edits a local env file in place (with a timestamped backup);
* this script writes a **new candidate file** whose path the caller names, so the
  values can be reviewed and handed to a platform secret store, then applied by a
  restart — no in-place edit of the live env file, no backup to forget.

Safety rules (each one is asserted by ``tests/ops_rotate_secrets_candidate_test.py``):

* **dry run is the default** — nothing is written without ``--out``;
* **no secret is ever printed** — stdout carries names and short SHA-256
  fingerprints only;
* the candidate file is written with mode **0600** and refuses to overwrite an
  existing file unless ``--force`` is passed;
* ``--out`` may not point inside ``data/`` (or any ``data`` directory) and the
  script never reads or writes the data directory.

Names come from the files that actually read them, not from a guess:

* ``.env.example`` — ``EINVITE_SECRET_KEY`` (line 17, "auto-generated if blank"),
  ``EINVITE_BILLING_WEBHOOK_SECRET`` (line 65), ``EINVITE_STRIPE_WEBHOOK_SECRET``
  (line 76);
* ``core/preflight.py`` ``SECRET_NAMES`` — the three signing secrets required in
  production (``--with-preflight``);
* ``core/crypto.py`` — ``EINVITE_FIELD_ENCRYPTION_KEY`` and its ``_PREVIOUS``
  window (``--field-encryption`` only; the default refuses to touch it).

Usage::

    scripts/rotate-secrets.py --env-file .env                  # dry run (default)
    scripts/rotate-secrets.py --env-file .env --out /tmp/new.env
    scripts/rotate-secrets.py --env-file .env --out /tmp/new.env --with-preflight
    scripts/rotate-secrets.py --env-file .env --out /tmp/new.env --field-encryption

Exit codes: 0 success · 1 error · 2 field key not present in the source env file
(nothing was written) · 3 refused to overwrite an existing ``--out`` file.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import secrets
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Self-issued secrets: see the module docstring for the exact source lines.
DEFAULT_NAMES = (
    "EINVITE_SECRET_KEY",
    "EINVITE_BILLING_WEBHOOK_SECRET",
    "EINVITE_STRIPE_WEBHOOK_SECRET",
)
#: ``core/preflight.py`` SECRET_NAMES — required by production startup.
PREFLIGHT_NAMES = (
    "EINVITE_UPLOAD_SIGNING_SECRET",
    "EINVITE_MEDIA_SIGNING_SECRET",
    "EINVITE_GUEST_TOKEN_SECRET",
)
FIELD_KEY = "EINVITE_FIELD_ENCRYPTION_KEY"
FIELD_PREVIOUS = "EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS"

#: Documented as provider-issued in docs/ops/SECRETS-ROTATION.md. Listed so the
#: dry run reminds the operator; never generated here.
PROVIDER_ISSUED = {
    "EINVITE_SMTP_PASSWORD": "your SMTP provider",
    "EINVITE_OBJECT_STORAGE_ACCESS_KEY": "your S3/R2 provider",
    "EINVITE_OBJECT_STORAGE_SECRET_KEY": "your S3/R2 provider",
    "EINVITE_BILLING_API_KEY": "your billing provider",
    "EINVITE_STRIPE_SECRET_KEY": "the Stripe dashboard",
    "EINVITE_CANVA_CLIENT_SECRET": "the Canva developer console",
    "EINVITE_BOT_PROTECTION_SECRET": "your Turnstile/reCAPTCHA console",
}


def fingerprint(value: str | None) -> str:
    """Short hash that lets an operator match a value without seeing it."""
    if not value:
        return "unset"
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$", line)
        if match:
            values.setdefault(match.group(1), match.group(2).strip().strip('"').strip("'"))
    return values


def generate(name: str) -> str:
    if name.endswith("_ENCRYPTION_KEY"):
        from cryptography.fernet import Fernet

        return Fernet.generate_key().decode("ascii")
    return secrets.token_urlsafe(48)


def _inside_data_dir(path: Path) -> bool:
    """True when any path component is a ``data`` directory."""
    return any(part == "data" for part in path.parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rotate long-lived secrets into a candidate env file (dry run by default).",
    )
    parser.add_argument("--env-file", default=str(REPO_ROOT / ".env"),
                        help="source env file used only to fingerprint current values")
    parser.add_argument("--out", help="write the candidate file here (default: dry run)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing --out file")
    parser.add_argument("--with-preflight", action="store_true",
                        help="also rotate the three production signing secrets")
    parser.add_argument("--field-encryption", action="store_true",
                        help="rotate the Fernet field key using its previous-key window")
    args = parser.parse_args(argv)

    env_file = Path(args.env_file).expanduser().resolve()
    current = read_env(env_file)
    updates: dict[str, str] = {}

    names = list(DEFAULT_NAMES) + (list(PREFLIGHT_NAMES) if args.with_preflight else [])
    for name in names:
        updates[name] = generate(name)
        print(f"  {name}: {fingerprint(current.get(name))} -> {fingerprint(updates[name])}")

    rc = 0
    if args.field_encryption:
        active = current.get(FIELD_KEY, "")
        if not active:
            print(
                f"  {FIELD_KEY}: not in {env_file} — refusing to guess the active key; nothing "
                f"was written for it. If it lives in <data-dir>/.field-encryption-key, copy that "
                f"value into {FIELD_PREVIOUS} first or put it in {env_file}.",
                file=sys.stderr,
            )
            rc = 2
        else:
            try:
                from cryptography.fernet import Fernet

                Fernet(active.encode("ascii"))
            except Exception:
                print(f"  {FIELD_KEY}: the value in {env_file} is not a valid Fernet key — not rotating it.",
                      file=sys.stderr)
                rc = 1
            else:
                updates[FIELD_KEY] = generate(FIELD_KEY)
                updates[FIELD_PREVIOUS] = active
                print(f"  {FIELD_KEY}: {fingerprint(active)} -> {fingerprint(updates[FIELD_KEY])} "
                      f"(old kept as {FIELD_PREVIOUS})")
                print(f"    Next: run scripts/migrate_encrypt_sensitive_fields.py --data-dir <dir> "
                      f"--reencrypt while both keys are set, then drop {FIELD_PREVIOUS}.")

    for name, provider in PROVIDER_ISSUED.items():
        print(f"  {name}: provider-issued — rotate at {provider} (see docs/ops/SECRETS-ROTATION.md)")

    if rc:
        return rc

    if not args.out:
        print(f"dry-run: {len(updates)} value(s) would be written to a candidate file; nothing written.")
        print("pass --out PATH (outside data/) to write it with mode 0600.")
        return 0

    out = Path(args.out).expanduser().resolve()
    if _inside_data_dir(out):
        print(f"refusing to write inside a data directory: {out}", file=sys.stderr)
        return 1
    if out.exists() and not args.force:
        print(f"refusing to overwrite existing {out}; pass --force or choose another path.", file=sys.stderr)
        return 3

    lines = [
        "# Rotated by scripts/rotate-secrets.py — candidate values, mode 0600.",
        "# Apply: merge into the host's secret store / env file, restart, verify, then",
        "# revoke the old values. Docs: docs/ops/SECRETS-ROTATION.md",
        f"# Generated: {env_file}",
        "",
    ]
    lines += [f"{name}={value}" for name, value in updates.items()]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out.chmod(0o600)
    print(f"wrote {len(updates)} value(s) to {out} (mode 0600); values were not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

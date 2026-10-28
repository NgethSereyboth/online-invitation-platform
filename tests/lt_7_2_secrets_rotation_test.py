#!/usr/bin/env python3
"""LT-7.2 step 7 — secrets rotation: script + field-encryption re-encryption (ROADMAP §4.7).

Part 1 — `scripts/rotate-secrets.sh` against a temporary env file:

* generated secrets are replaced with strong new values and the old file is kept
  as a timestamped backup;
* stdout carries fingerprints only — never the values (unless `--print`);
* `--dry-run` writes nothing;
* `--field-encryption` moves the old key to `EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS`
  and writes a valid new Fernet key;
* a missing active key is refused (exit 2) without touching the file.

Part 2 — the `--reencrypt` pass on a temp database only:

* encrypt the fixture rows under key A, then re-encrypt with key B while A is set
  as the previous key; every ciphertext must end up readable by B alone;
* legacy plaintext rows are left alone;
* a wrong key with no previous key is refused (exit 1) and the ciphertext is not
  destroyed.

Prints ``LT_7_2_SECRETS_ROTATION_PASSED`` on success.
"""
from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))

from v14_test_utils import temporary_data  # noqa: E402

SCRIPT = REPO / "scripts" / "rotate-secrets.sh"
MIGRATE = REPO / "scripts" / "migrate_encrypt_sensitive_fields.py"

PROBE = """
import sqlite3, sys
sys.path.insert(0, "src/python")
from core.crypto import decrypt_field, is_current_key_ciphertext
db, sql = sys.argv[1], sys.argv[2]
value = sqlite3.connect(db).execute(sql).fetchone()[0]
print("VALUE=" + repr(value))
print("CURRENT=" + str(is_current_key_ciphertext(value)))
print("PLAIN=" + repr(decrypt_field(value)))
"""


def _probe(db_file: Path, sql: str, key: str, previous: str | None = None) -> dict:
    env = {**os.environ, "EINVITE_FIELD_ENCRYPTION_KEY": key}
    if previous:
        env["EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS"] = previous
    else:
        env.pop("EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS", None)
    result = subprocess.run(
        [sys.executable, "-c", PROBE, str(db_file), sql],
        capture_output=True, text=True, cwd=REPO, env=env,
    )
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    out = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            name, _, value = line.partition("=")
            out[name] = value
    return out


def _run_script(env_file: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), "--env-file", str(env_file), *extra],
        capture_output=True, text=True, cwd=REPO, env=os.environ.copy(),
    )


def _read_env(path: Path) -> dict:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def _run_migrate(data_dir: Path, key: str, *extra: str, previous: str | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "EINVITE_FIELD_ENCRYPTION_KEY": key}
    if previous:
        env["EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS"] = previous
    else:
        env.pop("EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS", None)
    return subprocess.run(
        [sys.executable, str(MIGRATE), "--data-dir", str(data_dir), *extra],
        capture_output=True, text=True, cwd=REPO, env=env,
    )


def test_rotate_secrets_script_on_a_temp_env_file():
    with temporary_data("einvite-lt-7-2-rotate-") as tmp:
        env_file = tmp / "env"
        key_a = Fernet.generate_key().decode("ascii")
        env_file.write_text(
            "# fixture env\n"
            "EINVITE_SECRET_KEY=old-secret-value\n"
            "EINVITE_BILLING_WEBHOOK_SECRET=old-billing\n"
            "EINVITE_STRIPE_WEBHOOK_SECRET=old-stripe\n"
            f"EINVITE_FIELD_ENCRYPTION_KEY={key_a}\n",
            encoding="utf-8",
        )
        before = env_file.read_text(encoding="utf-8")
        old_values = _read_env(env_file)

        dry = _run_script(env_file, "--field-encryption", "--dry-run")
        assert dry.returncode == 0, (dry.stdout, dry.stderr)
        assert env_file.read_text(encoding="utf-8") == before, "dry-run must not write"

        rotated = _run_script(env_file, "--field-encryption")
        assert rotated.returncode == 0, (rotated.stdout, rotated.stderr)
        assert "sha256:" in rotated.stdout
        values = _read_env(env_file)
        for name in ("EINVITE_SECRET_KEY", "EINVITE_BILLING_WEBHOOK_SECRET", "EINVITE_STRIPE_WEBHOOK_SECRET"):
            assert values[name] != old_values[name], f"{name} was not rotated"
            assert values[name] and values[name] not in rotated.stdout, f"{name} leaked to stdout"
        assert len(values["EINVITE_SECRET_KEY"]) >= 40
        assert values["EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS"] == key_a
        Fernet(values["EINVITE_FIELD_ENCRYPTION_KEY"].encode("ascii"))  # valid Fernet key
        backups = list(tmp.glob("env.bak-*"))
        assert backups and backups[0].read_text(encoding="utf-8") == before

        dry = _run_script(env_file, "--dry-run")
        assert dry.returncode == 0
        assert "dry-run" in dry.stdout

        printed = _run_script(env_file, "--print")
        assert printed.returncode == 0, (printed.stdout, printed.stderr)
        latest = _read_env(env_file)
        assert f"PRINT EINVITE_SECRET_KEY={latest['EINVITE_SECRET_KEY']}" in printed.stdout

        # A missing field key is refused with exit 2 and nothing is written.
        missing = tmp / "env-missing"
        missing.write_text("EINVITE_SECRET_KEY=still-here\n", encoding="utf-8")
        refused = _run_script(missing, "--field-encryption")
        assert refused.returncode == 2, (refused.returncode, refused.stdout, refused.stderr)
        assert missing.read_text(encoding="utf-8") == "EINVITE_SECRET_KEY=still-here\n"
        print("[OK] rotate-secrets.sh: fingerprints only, backup kept, dry-run inert, missing key refused", flush=True)


def test_field_key_reencryption_pass():
    with temporary_data("einvite-lt-7-2-reencrypt-") as data_dir:
        db_file = data_dir / "invites.db"
        connection = sqlite3.connect(str(db_file))
        try:
            connection.execute("CREATE TABLE users(id TEXT PRIMARY KEY, email TEXT)")
            connection.execute("CREATE TABLE guests(id TEXT PRIMARY KEY, email TEXT, phone TEXT)")
            connection.execute("INSERT INTO users(id,email) VALUES('u1','Rotate.Me@einvite.test')")
            connection.execute("INSERT INTO guests(id,email,phone) VALUES('g1','guest@einvite.test','+855 10 000 000')")
            connection.commit()
        finally:
            connection.close()

        key_a = Fernet.generate_key().decode("ascii")
        key_b = Fernet.generate_key().decode("ascii")
        key_c = Fernet.generate_key().decode("ascii")
        row = "SELECT email FROM users WHERE id='u1'"

        applied = _run_migrate(data_dir, key_a)
        assert applied.returncode == 0, (applied.stdout, applied.stderr)
        assert _probe(db_file, row, key_a)["CURRENT"] == "True"
        assert _probe(db_file, row, key_b)["CURRENT"] == "False"

        # A legacy plaintext row created after the migration must stay untouched.
        connection = sqlite3.connect(str(db_file))
        try:
            connection.execute("INSERT INTO users(id,email) VALUES('u2','Legacy@einvite.test')")
            connection.commit()
        finally:
            connection.close()

        dry = _run_migrate(data_dir, key_b, "--reencrypt", "--dry-run", previous=key_a)
        assert dry.returncode == 0, (dry.stdout, dry.stderr)
        assert "re-encrypted 1 row(s)" in dry.stdout, dry.stdout

        done = _run_migrate(data_dir, key_b, "--reencrypt", previous=key_a)
        assert done.returncode == 0, (done.stdout, done.stderr)
        # users.email + guests.email + guests.phone were all encrypted under A.
        assert "total: 3 row(s) now under the active key" in done.stdout, done.stdout
        after = _probe(db_file, row, key_b)
        assert after["CURRENT"] == "True", after
        assert after["PLAIN"] == repr("Rotate.Me@einvite.test"), after
        assert _probe(db_file, row, key_a)["CURRENT"] == "False"
        phone = _probe(db_file, "SELECT phone FROM guests WHERE id='g1'", key_b)
        assert phone["CURRENT"] == "True" and phone["PLAIN"] == repr("+855 10 000 000"), phone
        legacy = _probe(db_file, "SELECT email FROM users WHERE id='u2'", key_b)
        assert legacy["VALUE"] == repr("Legacy@einvite.test"), legacy
        assert legacy["CURRENT"] == "False"

        # A wrong active key with no previous key must refuse, not destroy data.
        stored_before = _probe(db_file, row, key_b)["VALUE"]
        refused = _run_migrate(data_dir, key_c, "--reencrypt")
        assert refused.returncode == 1, (refused.returncode, refused.stdout, refused.stderr)
        assert "could not be decrypted" in refused.stderr, refused.stderr
        assert _probe(db_file, row, key_b)["VALUE"] == stored_before
        print("[OK] re-encryption pass: A -> B, plaintext untouched, wrong key refused", flush=True)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-x", "-q"]))

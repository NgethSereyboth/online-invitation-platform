#!/usr/bin/env python3
"""B-3 — `scripts/rotate-secrets.py` writes a safe candidate file (ROADMAP §4.7).

The `.sh` companion edits a local env file in place and is covered by
`tests/lt_7_2_secrets_rotation_test.py`. The host/secret-store flow needs the
other shape: a **candidate file** at a caller-named path that can be reviewed and
applied by a restart, with dry run as the default.

Asserted here:

* dry run (no `--out`) writes nothing and prints fingerprints only;
* a real run writes mode 0600 with fresh values for every documented name and
  prints none of them;
* `--with-preflight` adds the three production signing secrets;
* `--field-encryption` refuses (exit 2, no file) when the active key is absent,
  and emits current + `_PREVIOUS` when a valid Fernet key is present;
* an existing `--out` is refused without `--force`;
* `--out` inside a `data` directory is refused.
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "rotate-secrets.py"

OLD = {
    "EINVITE_SECRET_KEY": "old-secret-key-value",
    "EINVITE_BILLING_WEBHOOK_SECRET": "old-billing-value",
    "EINVITE_STRIPE_WEBHOOK_SECRET": "old-stripe-value",
}


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _env_file(tmp_path: Path, extra: dict | None = None) -> Path:
    path = tmp_path / "source.env"
    lines = [f"{name}={value}" for name, value in OLD.items()]
    lines += [f"{name}={value}" for name, value in (extra or {}).items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _parse(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            name, _, value = line.partition("=")
            values[name] = value
    return values


def test_dry_run_is_the_default_and_writes_nothing(tmp_path):
    source = _env_file(tmp_path)
    proc = _run("--env-file", str(source))
    assert proc.returncode == 0, proc.stderr
    assert "dry-run" in proc.stdout
    assert not (tmp_path / "candidate.env").exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["source.env"], "dry run created something"
    # Fingerprints, not values.
    assert "sha256:" in proc.stdout
    for value in OLD.values():
        assert value not in proc.stdout


def test_real_run_writes_0600_with_fresh_values_and_prints_none(tmp_path):
    source = _env_file(tmp_path)
    out = tmp_path / "candidate.env"
    proc = _run("--env-file", str(source), "--out", str(out))
    assert proc.returncode == 0, proc.stderr

    values = _parse(out)
    assert set(values) == {
        "EINVITE_SECRET_KEY",
        "EINVITE_BILLING_WEBHOOK_SECRET",
        "EINVITE_STRIPE_WEBHOOK_SECRET",
    }
    for name, old in OLD.items():
        assert values[name] and values[name] != old, f"{name} was not rotated"
        assert len(values[name]) >= 32, f"{name} is shorter than the production floor"
        assert values[name] not in proc.stdout
        assert values[name] not in proc.stderr
    mode = stat.S_IMODE(out.stat().st_mode)
    assert mode == 0o600, f"candidate mode is {oct(mode)}"
    assert "values were not printed" in proc.stdout


def test_with_preflight_adds_the_three_signing_secrets(tmp_path):
    source = _env_file(tmp_path)
    out = tmp_path / "candidate.env"
    proc = _run("--env-file", str(source), "--out", str(out), "--with-preflight")
    assert proc.returncode == 0, proc.stderr
    values = _parse(out)
    for name in (
        "EINVITE_UPLOAD_SIGNING_SECRET",
        "EINVITE_MEDIA_SIGNING_SECRET",
        "EINVITE_GUEST_TOKEN_SECRET",
    ):
        assert name in values, name
        assert len(values[name]) >= 32
        assert values[name] not in proc.stdout


def test_field_encryption_refuses_without_the_active_key(tmp_path):
    source = _env_file(tmp_path)
    out = tmp_path / "candidate.env"
    proc = _run("--env-file", str(source), "--out", str(out), "--field-encryption")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert not out.exists(), "a refused rotation must not write a candidate file"


def test_field_encryption_emits_current_and_previous(tmp_path):
    active = Fernet.generate_key().decode("ascii")
    source = _env_file(tmp_path, {"EINVITE_FIELD_ENCRYPTION_KEY": active})
    out = tmp_path / "candidate.env"
    proc = _run("--env-file", str(source), "--out", str(out), "--field-encryption")
    assert proc.returncode == 0, proc.stderr
    values = _parse(out)
    assert values["EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS"] == active
    assert values["EINVITE_FIELD_ENCRYPTION_KEY"] != active
    Fernet(values["EINVITE_FIELD_ENCRYPTION_KEY"].encode("ascii"))  # valid new key
    assert values["EINVITE_FIELD_ENCRYPTION_KEY"] not in proc.stdout
    assert active not in proc.stdout


def test_existing_out_needs_force(tmp_path):
    source = _env_file(tmp_path)
    out = tmp_path / "candidate.env"
    out.write_text("KEEP=me\n", encoding="utf-8")
    refused = _run("--env-file", str(source), "--out", str(out))
    assert refused.returncode == 3
    assert out.read_text(encoding="utf-8") == "KEEP=me\n"
    forced = _run("--env-file", str(source), "--out", str(out), "--force")
    assert forced.returncode == 0, forced.stderr
    assert "EINVITE_SECRET_KEY" in _parse(out)


def test_refuses_to_write_inside_a_data_directory(tmp_path):
    source = _env_file(tmp_path)
    out = tmp_path / "data" / "candidate.env"
    proc = _run("--env-file", str(source), "--out", str(out))
    assert proc.returncode == 1
    assert not out.exists()
    assert "data directory" in proc.stderr


def test_env_file_values_are_used_for_fingerprints_only(tmp_path):
    source = _env_file(tmp_path)
    out = tmp_path / "candidate.env"
    proc = _run("--env-file", str(source), "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    # No generated value echoes an old one, and the source file is untouched.
    values = _parse(out)
    assert source.read_text(encoding="utf-8") == "\n".join(f"{k}={v}" for k, v in OLD.items()) + "\n"
    assert not set(values.values()) & set(OLD.values())

"""
core/crypto.py — Part 4 Task 4.1 (ROADMAP-v0.54-to-v1.0 §4.1)

Field-level encryption for sensitive database columns.

Uses ``cryptography.fernet.Fernet`` (AES-128-CBC + HMAC-SHA256) to encrypt
sensitive fields at the application layer. The key is stored in
``EINVITE_FIELD_ENCRYPTION_KEY`` (64-byte urlsafe base64) and auto-generated
on first boot via ``features.secrets.ensure_secret``.

For lookup columns (e.g. ``users.email``), store a separate ``email_hash``
column (SHA-256 of lowercased email) with an index. Encrypt the original for
display. Lookup goes through the hash; decryption only happens when the
plaintext is needed.

Usage:
    from core.crypto import encrypt_field, decrypt_field, hash_for_lookup
    encrypted = encrypt_field("user@example.com")  # b64 string
    plaintext = decrypt_field(encrypted)             # "user@example.com"
    email_hash = hash_for_lookup("user@example.com") # SHA-256 hex
"""

from __future__ import annotations
import base64
import hashlib
import os
import sys
from pathlib import Path

# Ensure we can import core.config / features.* when this module is imported
# from a script that did not add src/python to sys.path itself.
_PYTHON_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PYTHON_ROOT))
try:
    from core.config import get as _config_get
except ImportError:  # pragma: no cover - only when the package layout moved
    def _config_get(name, default=None):
        return os.environ.get(name, default)

_FERNET = None
_FERNET_KEY = None
_FERNET_PREVIOUS = None
_KEY_ENV = "EINVITE_FIELD_ENCRYPTION_KEY"
#: Set only while rotating the field-encryption key: old ciphertexts keep
#: decrypting until ``--reencrypt`` has rewritten them under the new key.
_PREV_KEY_ENV = "EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS"
_KEY_FILE = ".field-encryption-key"
#: Set to 0/false/no to stop encrypting new values. Reads keep decrypting, so
#: disabling this never strands data that was already encrypted.
_ENABLED_ENV = "EINVITE_FIELD_ENCRYPTION"
_LAST_KEY_REASON = "uninitialised"


def _data_dir() -> Path:
    """The directory holding this deployment's data (mirrors server.DATA)."""
    return Path(_config_get("EINVITE_DATA_DIR", str(_PYTHON_ROOT / "data"))).expanduser()


def _valid_key(value) -> bool:
    """True when ``value`` is a usable Fernet key (32 urlsafe-base64 bytes)."""
    if isinstance(value, str):
        value = value.strip().encode("ascii", "ignore")
    if not value:
        return False
    try:
        from cryptography.fernet import Fernet
        Fernet(value)
        return True
    except Exception:
        return False


def encryption_enabled() -> bool:
    """False only when ``EINVITE_FIELD_ENCRYPTION`` is explicitly off."""
    value = str(_config_get(_ENABLED_ENV, "1") or "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _generate_key() -> str:
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode("ascii")


def _load_or_create_key() -> tuple[str, str]:
    """Resolve the encryption key. Returns ``(key, reason)``.

    Order: ``EINVITE_FIELD_ENCRYPTION_KEY`` (must be a valid Fernet key) → the
    per-data-dir sidecar ``.field-encryption-key`` → a freshly generated key
    persisted to that sidecar (0600). The sidecar lives with the data it
    encrypts, so the key survives a restart; only a read-only data directory
    falls back to a process-local key, which is reported as such.
    """
    configured = str(_config_get(_KEY_ENV, "") or "").strip()
    if configured:
        if _valid_key(configured):
            return configured, "env"
        # A wrong-shaped env value must not silently disable encryption; say so.
        return _generate_key(), "env-invalid"
    path = _data_dir() / _KEY_FILE
    try:
        if path.is_file():
            stored = path.read_text(encoding="utf-8").strip()
            if _valid_key(stored):
                return stored, "sidecar"
        key = _generate_key()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(key, encoding="utf-8")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return key, "generated"
    except OSError:
        return _generate_key(), "ephemeral"


def _get_fernet():
    """Lazily initialise the Fernet instance from the resolved key."""
    global _FERNET, _FERNET_KEY, _LAST_KEY_REASON
    if _FERNET is not None:
        return _FERNET
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        raise RuntimeError(
            "cryptography library not installed. Run: pip install cryptography"
        )
    key, reason = _load_or_create_key()
    _FERNET_KEY = key
    _LAST_KEY_REASON = reason
    _FERNET = Fernet(key.encode("ascii"))
    return _FERNET


def reset_key_cache() -> None:
    """Drop the cached Fernet(s) so the next call re-resolves the key.

    For a test (or a rotation performed in-process) that points
    ``EINVITE_FIELD_ENCRYPTION_KEY`` at another key after this module already
    resolved one; without this the first key of the process sticks.
    """
    global _FERNET, _FERNET_KEY, _FERNET_PREVIOUS, _LAST_KEY_REASON
    _FERNET = None
    _FERNET_KEY = None
    _FERNET_PREVIOUS = None
    _LAST_KEY_REASON = "uninitialised"


def key_source() -> str:
    """Where the active key came from (diagnostics/preflight, never the key itself)."""
    _get_fernet()
    return _LAST_KEY_REASON


def key_fingerprint() -> str:
    """Short SHA-256 of the active key — lets an operator match two processes'
    keys without ever printing the key itself."""
    _get_fernet()
    return hashlib.sha256(str(_FERNET_KEY).encode("utf-8")).hexdigest()[:12]


def _get_previous_fernet():
    """Fernet for ``EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS``, or None.

    Decrypt-only: every new write uses the active key. Set during a rotation
    window so reads keep working until the re-encryption pass has run.
    """
    global _FERNET_PREVIOUS
    if _FERNET_PREVIOUS is not None:
        return _FERNET_PREVIOUS
    configured = str(_config_get(_PREV_KEY_ENV, "") or "").strip()
    if not configured or not _valid_key(configured):
        return None
    from cryptography.fernet import Fernet
    _FERNET_PREVIOUS = Fernet(configured.encode("ascii"))
    return _FERNET_PREVIOUS


def encrypt_field(plaintext: str | None) -> str | None:
    """Encrypt a plaintext string. Returns None if input is None."""
    if plaintext is None:
        return None
    if not plaintext:
        return ""
    if not encryption_enabled():
        return plaintext
    f = _get_fernet()
    encrypted = f.encrypt(plaintext.encode("utf-8"))
    return encrypted.decode("ascii")


def decrypt_field(ciphertext: str | None) -> str | None:
    """Decrypt a ciphertext string. Returns None if input is None.

    Tries the active key, then ``EINVITE_FIELD_ENCRYPTION_KEY_PREVIOUS`` (set
    only during a rotation window), and finally returns the input unchanged for
    legacy plaintext. Re-encrypt rows with the active key before unsetting the
    previous one (``scripts/migrate_encrypt_sensitive_fields.py --reencrypt``).
    """
    if ciphertext is None:
        return None
    if not ciphertext:
        return ""
    try:
        decrypted = _get_fernet().decrypt(ciphertext.encode("ascii"))
        return decrypted.decode("utf-8")
    except Exception:
        pass
    previous = _get_previous_fernet()
    if previous is not None:
        try:
            return previous.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except Exception:
            pass
    # Not encrypted (legacy data) — return as-is
    return ciphertext


def hash_for_lookup(plaintext: str | None) -> str | None:
    """Compute a SHA-256 hash of the lowercased plaintext for indexed lookups."""
    if plaintext is None:
        return None
    if not plaintext:
        return ""
    return hashlib.sha256(plaintext.lower().strip().encode("utf-8")).hexdigest()


def is_encryption_configured() -> bool:
    """Return True if EINVITE_FIELD_ENCRYPTION_KEY is set in the environment."""
    return bool(os.environ.get(_KEY_ENV, "").strip())


# Alias for clarity at call sites
email_hash = hash_for_lookup

# Alias for the bootstrap check
is_encryption_active = is_encryption_configured

# Fernet ciphertexts start with "gAAAAA" — used to detect if a field is already encrypted
CIPHERTEXT_PREFIX = "gAAAAA"


def is_current_key_ciphertext(value: str | None) -> bool:
    """True when ``value`` is a ciphertext the active key can read.

    A row encrypted under the previous key still *decrypts* (fallback) but fails
    this check — that is what ``--reencrypt`` selects during a rotation.
    """
    if not value or not isinstance(value, str) or not value.startswith(CIPHERTEXT_PREFIX):
        return False
    try:
        return _get_fernet().decrypt(value.encode("ascii")) is not None
    except Exception:
        return False


def verify_email_hash(plaintext: str, stored_hash: str | None) -> bool:
    """Verify that a plaintext matches a stored SHA-256 hash."""
    if not stored_hash:
        return False
    return hash_for_lookup(plaintext) == stored_hash


def encryption_available() -> bool:
    """True when a value can actually be encrypted and decrypted back.

    Stronger than :func:`is_encryption_configured` (which only reports whether
    the env var is set): this proves the resolved key works, which is what the
    migration script and the startup log need.
    """
    if not encryption_enabled():
        return False
    try:
        probe = "field-encryption-probe"
        return decrypt_field(encrypt_field(probe)) == probe
    except Exception:
        return False


def ensure_encryption_key():
    """Resolve (and, on first boot, generate + persist) the encryption key.

    Called at server startup so a missing key is created before the first
    write, instead of during it. Returns the key; use :func:`key_source` and
    :func:`key_fingerprint` for diagnostics rather than logging the value.
    """
    _get_fernet()
    return str(_FERNET_KEY)

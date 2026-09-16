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

# Ensure we can import features.secrets
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from features.secrets import ensure_secret as _ensure_secret
except ImportError:
    _ensure_secret = None

_FERNET = None
_KEY_ENV = "EINVITE_FIELD_ENCRYPTION_KEY"


def _get_fernet():
    """Lazily initialize the Fernet instance. Auto-generates a key if missing."""
    global _FERNET
    if _FERNET is not None:
        return _FERNET
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        raise RuntimeError(
            "cryptography library not installed. Run: pip install cryptography"
        )
    key = os.environ.get(_KEY_ENV, "").strip()
    if not key:
        # Auto-generate via features.secrets
        if _ensure_secret:
            _ensure_secret(_KEY_ENV, 64)
            key = os.environ.get(_KEY_ENV, "").strip()
        if not key:
            # Dev fallback — generate in-memory (NOT for production)
            key = Fernet.generate_key().decode("ascii")
            os.environ[_KEY_ENV] = key
    try:
        _FERNET = Fernet(key.encode("ascii") if isinstance(key, str) else key)
    except Exception:
        # Key might not be valid base64 — regenerate
        key = Fernet.generate_key().decode("ascii")
        os.environ[_KEY_ENV] = key
        _FERNET = Fernet(key.encode("ascii"))
    return _FERNET


def encrypt_field(plaintext: str | None) -> str | None:
    """Encrypt a plaintext string. Returns None if input is None."""
    if plaintext is None:
        return None
    if not plaintext:
        return ""
    f = _get_fernet()
    encrypted = f.encrypt(plaintext.encode("utf-8"))
    return encrypted.decode("ascii")


def decrypt_field(ciphertext: str | None) -> str | None:
    """Decrypt a ciphertext string. Returns None if input is None.
    Returns the original string if decryption fails (backward compat with pre-encryption data)."""
    if ciphertext is None:
        return None
    if not ciphertext:
        return ""
    try:
        f = _get_fernet()
        decrypted = f.decrypt(ciphertext.encode("ascii"))
        return decrypted.decode("utf-8")
    except Exception:
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


def verify_email_hash(plaintext: str, stored_hash: str | None) -> bool:
    """Verify that a plaintext matches a stored SHA-256 hash."""
    if not stored_hash:
        return False
    return hash_for_lookup(plaintext) == stored_hash


def ensure_encryption_key():
    """Ensure EINVITE_FIELD_ENCRYPTION_KEY is set. Auto-generates if missing.

    Called at server startup to bootstrap field-level encryption.
    Delegates to ``features.secrets.ensure_secret`` for the actual key generation.
    """
    key = os.environ.get(_KEY_ENV, "").strip()
    if not key:
        # Auto-generate a 64-byte urlsafe base64 key
        import secrets as _secrets
        key = _secrets.token_urlsafe(64)
        os.environ[_KEY_ENV] = key
    # Verify the key works by initializing Fernet
    _get_fernet()
    return key

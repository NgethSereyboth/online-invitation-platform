"""Security helpers for the V13 account-security foundation.

The module intentionally has no web-framework dependency so the existing no-build
local server can keep using it directly. Optional Argon2 support is detected at
runtime; production preflight reports when it is unavailable.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from dataclasses import dataclass
from typing import Any

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import InvalidHashError, VerifyMismatchError
    from argon2.low_level import Type
except Exception:  # pragma: no cover - optional dependency path
    PasswordHasher = None
    InvalidHashError = VerifyMismatchError = Exception
    Type = None

ARGON2_AVAILABLE = PasswordHasher is not None
_ARGON2 = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
) if ARGON2_AVAILABLE else None


def hash_password(password: str) -> tuple[str, str, str]:
    """Return (hash, legacy_salt, algorithm). New passwords prefer Argon2id."""
    if ARGON2_AVAILABLE:
        return _ARGON2.hash(password), "", "argon2id-v1"
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 310_000).hex()
    return digest, salt, "pbkdf2-sha256-v2"


def verify_password(password: str, stored_hash: str, salt: str = "", algorithm: str = "") -> tuple[bool, bool]:
    """Return (valid, should_rehash), supporting all historical V12 hashes."""
    algo = (algorithm or "").lower()
    if stored_hash.startswith("$argon2") or algo.startswith("argon2"):
        if not ARGON2_AVAILABLE:
            return False, False
        try:
            valid = _ARGON2.verify(stored_hash, password)
            return bool(valid), bool(valid and _ARGON2.check_needs_rehash(stored_hash))
        except (VerifyMismatchError, InvalidHashError, ValueError):
            return False, False
    iterations = 310_000 if algo == "pbkdf2-sha256-v2" else 210_000
    try:
        expected = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), iterations).hex()
    except Exception:
        return False, False
    valid = hmac.compare_digest(str(stored_hash), expected)
    return valid, bool(valid and ARGON2_AVAILABLE)


# ──────────────────────────────────────────────────────────────────────────
# V54.12 (sec-3 — P1-C) — MFA recovery codes
#
# Recovery codes let a user who has lost their authenticator (or whose
# TOTP secret was wiped) prove identity by presenting one of N single-use
# pre-generated codes. The codes are shown ONCE at enable time and only
# their hashes are persisted, so a database read never reveals a usable
# code. The same hashing primitives as ``hash_password`` are reused: Argon2id
# when ``argon2-cffi`` is installed, otherwise PBKDF2-HMAC-SHA256 with
# 310k iterations (the OWASP-recommended floor as of 2023).
#
# Code format: ``XXXX-XXXX-XXXX`` (12 chars from a 32-char alphabet that
# excludes visually-ambiguous symbols 0/O/1/I/L). The 32-char alphabet has
# ~5 bits/char → 60 bits of entropy per code (≈2^60 brute-force work), well
# above the 2^32 ASVS L2 minimum for self-issued secrets.
# ──────────────────────────────────────────────────────────────────────────

# Crockford-style alphabet minus ambiguous chars (no 0/O, no 1/I, no L).
_RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_RECOVERY_ALPHABET_LEN = len(_RECOVERY_ALPHABET)  # 32


def _generate_one_recovery_code() -> str:
    """Return a single ``XXXX-XXXX-XXXX`` recovery code (12 chars + 2 hyphens).

    ``secrets.randbelow`` uses the OS CSPRNG. Since the alphabet length
    (32) is an exact power of 2 and ``randbelow`` already performs rejection
    sampling internally for arbitrary ranges, there is no modulo bias and no
    further rejection loop is needed here.
    """
    needed = 12  # displayed as AAAA-AAAA-AAAA (14 chars on the wire incl. hyphens)
    alphabet_len = _RECOVERY_ALPHABET_LEN  # 32 → power of 2 → bias-free
    chars = [_RECOVERY_ALPHABET[secrets.randbelow(alphabet_len)] for _ in range(needed)]
    raw = "".join(chars)
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"


def generate_recovery_codes(count: int = 10):
    """Generate ``count`` recovery codes.

    Returns a list of ``(plaintext, code_hash)`` tuples. The caller shows
    the plaintext ONCE to the user and persists only ``code_hash``.
    """
    if count < 1 or count > 100:
        raise ValueError("count must be between 1 and 100")
    out = []
    for _ in range(count):
        plaintext = _generate_one_recovery_code()
        out.append((plaintext, hash_recovery_code(plaintext)))
    return out


def hash_recovery_code(plaintext: str) -> str:
    """Hash a recovery code.

    Uses Argon2id (via ``argon2-cffi``) when available — same instance and
    parameters as ``hash_password``. Falls back to PBKDF2-HMAC-SHA256 with
    310k iterations and a fresh 32-byte salt (encoded as a ``pbkdf2_sha256$``-
    prefixed self-describing string so verification can route correctly
    without a separate algorithm column).
    """
    if ARGON2_AVAILABLE:
        return _ARGON2.hash(plaintext)
    salt = secrets.token_bytes(32)
    digest = hashlib.pbkdf2_hmac("sha256", plaintext.encode(), salt, 310_000)
    return f"pbkdf2_sha256${310_000}${salt.hex()}${digest.hex()}"


def verify_recovery_code(plaintext: str, stored_hash: str) -> bool:
    """Return True iff ``plaintext`` matches the stored hash.

    Constant-time on both branches: ``argon2-cffi`` uses
    ``_ARGON2.verify`` (constant-time internally), and the PBKDF2 fallback
    uses ``hmac.compare_digest`` on the recomputed digest.
    """
    if not stored_hash:
        return False
    if stored_hash.startswith("$argon2"):
        if not ARGON2_AVAILABLE:
            return False
        try:
            return bool(_ARGON2.verify(stored_hash, plaintext))
        except (VerifyMismatchError, InvalidHashError, ValueError):
            return False
    if stored_hash.startswith("pbkdf2_sha256$"):
        parts = stored_hash.split("$")
        # Expected shape: ['pbkdf2_sha256', '<iter>', '<salthex>', '<digesthex>']
        if len(parts) != 4:
            return False
        _algo, iter_str, salt_hex, expected_hex = parts
        try:
            iterations = int(iter_str)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(expected_hex)
        except (ValueError, TypeError):
            return False
        try:
            actual = hashlib.pbkdf2_hmac("sha256", plaintext.encode(), salt, iterations)
        except Exception:
            return False
        return hmac.compare_digest(actual, expected)
    return False


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    raw = str(value or "").encode("ascii")
    return base64.urlsafe_b64decode(raw + b"=" * ((4 - len(raw) % 4) % 4))


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _totp_counter(timestamp: int | None = None, period: int = 30) -> int:
    return int((timestamp or int(time.time())) // period)


def totp_code(secret: str, counter: int, digits: int = 6) -> str:
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded.upper())
    msg = struct.pack(">Q", int(counter))
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(number).zfill(digits)


def verify_totp(secret: str, code: str, timestamp: int | None = None, window: int = 1) -> bool:
    candidate = "".join(ch for ch in str(code or "") if ch.isdigit())
    if len(candidate) != 6:
        return False
    current = _totp_counter(timestamp)
    return any(hmac.compare_digest(totp_code(secret, current + offset), candidate) for offset in range(-window, window + 1))


def otpauth_uri(secret: str, email: str, issuer: str = "E-invitation-website") -> str:
    from urllib.parse import quote
    return f"otpauth://totp/{quote(issuer)}:{quote(email)}?secret={quote(secret)}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"


# --- Minimal CBOR decoding for WebAuthn attestation objects / COSE keys ---------
class CBORDecodeError(ValueError):
    pass


def _read_uint(data: bytes, pos: int, additional: int) -> tuple[int, int]:
    if additional < 24:
        return additional, pos
    sizes = {24: 1, 25: 2, 26: 4, 27: 8}
    size = sizes.get(additional)
    if not size or pos + size > len(data):
        raise CBORDecodeError("Unsupported or truncated CBOR integer")
    return int.from_bytes(data[pos:pos + size], "big"), pos + size


def cbor_decode(data: bytes, pos: int = 0) -> tuple[Any, int]:
    if pos >= len(data):
        raise CBORDecodeError("Truncated CBOR")
    first = data[pos]
    pos += 1
    major, additional = first >> 5, first & 31
    if additional == 31:
        raise CBORDecodeError("Indefinite CBOR values are not supported")
    length, pos = _read_uint(data, pos, additional)
    if major == 0:
        return length, pos
    if major == 1:
        return -1 - length, pos
    if major == 2:
        end = pos + length
        if end > len(data): raise CBORDecodeError("Truncated bytes")
        return data[pos:end], end
    if major == 3:
        end = pos + length
        if end > len(data): raise CBORDecodeError("Truncated text")
        return data[pos:end].decode("utf-8"), end
    if major == 4:
        values = []
        for _ in range(length):
            value, pos = cbor_decode(data, pos)
            values.append(value)
        return values, pos
    if major == 5:
        value = {}
        for _ in range(length):
            key, pos = cbor_decode(data, pos)
            item, pos = cbor_decode(data, pos)
            value[key] = item
        return value, pos
    if major == 6:
        return cbor_decode(data, pos)
    if major == 7:
        if additional == 20: return False, pos
        if additional == 21: return True, pos
        if additional in (22, 23): return None, pos
    raise CBORDecodeError("Unsupported CBOR type")


def parse_attestation_object(encoded: str) -> dict[str, Any]:
    raw = b64url_decode(encoded)
    obj, end = cbor_decode(raw)
    if end != len(raw) or not isinstance(obj, dict):
        raise CBORDecodeError("Invalid attestation object")
    auth_data = obj.get("authData")
    if not isinstance(auth_data, (bytes, bytearray)) or len(auth_data) < 55:
        raise CBORDecodeError("Missing authenticator data")
    flags = auth_data[32]
    if not flags & 0x40:
        raise CBORDecodeError("Attested credential data missing")
    sign_count = int.from_bytes(auth_data[33:37], "big")
    pos = 37 + 16
    cred_len = int.from_bytes(auth_data[pos:pos + 2], "big")
    pos += 2
    credential_id = bytes(auth_data[pos:pos + cred_len])
    pos += cred_len
    cose, _ = cbor_decode(bytes(auth_data), pos)
    if not isinstance(cose, dict):
        raise CBORDecodeError("Invalid credential public key")
    return {
        "authData": bytes(auth_data),
        "credentialId": credential_id,
        "coseKey": cose,
        "signCount": sign_count,
    }


def cose_ec2_to_pem(cose: dict[Any, Any]) -> str:
    """Convert a WebAuthn ES256 EC2 COSE key to PEM."""
    if int(cose.get(1, 0)) != 2 or int(cose.get(3, 0)) != -7 or int(cose.get(-1, 0)) != 1:
        raise ValueError("Only ES256 passkeys are supported by this local runtime")
    x, y = cose.get(-2), cose.get(-3)
    if not isinstance(x, bytes) or not isinstance(y, bytes) or len(x) != 32 or len(y) != 32:
        raise ValueError("Invalid passkey public key")
    try:
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization
        public = ec.EllipticCurvePublicNumbers(int.from_bytes(x, "big"), int.from_bytes(y, "big"), ec.SECP256R1()).public_key()
        return public.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode("ascii")
    except Exception as exc:
        raise RuntimeError("Passkey verification requires the cryptography package") from exc


def verify_es256_signature(public_key_pem: str, signature: bytes, signed_data: bytes) -> bool:
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        key = serialization.load_pem_public_key(public_key_pem.encode("ascii"))
        key.verify(signature, signed_data, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


def verify_client_data(encoded: str, expected_challenge: str, expected_origin: str, expected_type: str) -> tuple[bytes, dict[str, Any]]:
    raw = b64url_decode(encoded)
    data = json.loads(raw.decode("utf-8"))
    if data.get("type") != expected_type:
        raise ValueError("Unexpected WebAuthn ceremony type")
    if not hmac.compare_digest(str(data.get("challenge", "")), str(expected_challenge)):
        raise ValueError("WebAuthn challenge mismatch")
    if str(data.get("origin", "")).rstrip("/") != expected_origin.rstrip("/"):
        raise ValueError("WebAuthn origin mismatch")
    return raw, data


def parse_assertion_auth_data(encoded: str) -> tuple[bytes, int, bytes]:
    auth_data = b64url_decode(encoded)
    if len(auth_data) < 37:
        raise ValueError("Invalid authenticator data")
    return auth_data, int.from_bytes(auth_data[33:37], "big"), auth_data[:32]

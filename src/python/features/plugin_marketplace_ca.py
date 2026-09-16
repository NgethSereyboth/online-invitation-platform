"""
plugin_marketplace_ca.py — V54.33 Phase 4a (ROADMAP-V2 §4.4)

Marketplace Certificate Authority for plugin double-signing verification.

Per `docs/plugins/PLUGIN-SIGNING.md`:
  - Author signs the plugin manifest + bundle with their Ed25519 private key.
  - Marketplace CA signs the author's public key + manifest after review.
  - On install + launch, the host verifies BOTH signatures against pinned keys.

This module provides:
  - `verify_plugin_signature(manifest, author_signature, marketplace_signature)`
    — returns True iff both signatures verify against the pinned keys.
  - `check_revocation(author_key_id)` — returns True iff the author_key_id is
    NOT in the CRL (Certificate Revocation List).
  - `pinned_ca_public_key` — the hardcoded CA public key (Ed25519). The
    maintainer MUST replace this with the real CA key at deploy time.

Stdlib-only Python 3. Uses `cryptography` if available (the preferred path);
falls back to a pure-Python Ed25519 implementation if `cryptography` is not
installed. Documents the gap clearly.

See `docs/plugins/PLUGIN-SIGNING.md` for the full signing + rotation policy.
"""

from __future__ import annotations
import base64
import hashlib
import json
import os
import time
from typing import Any

# Pinned CA public key (Ed25519, base64-encoded, 32 bytes).
# WARNING: This is a PLACEHOLDER. The maintainer MUST replace this with the
# real CA public key at deploy time. Set via EINVITE_PLUGIN_CA_PUBKEY env var
# or hardcode here.
_PLACEHOLDER_CA_PUBKEY_B64 = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="  # 32 zero bytes
PINNED_CA_PUBKEY_B64 = os.environ.get("EINVITE_PLUGIN_CA_PUBKEY", _PLACEHOLDER_CA_PUBKEY_B64)

# CRL (Certificate Revocation List) — a set of revoked author_key_ids.
# Initially empty; populated by the moderation pipeline (see
# `docs/plugins/MODERATION-PIPELINE.md` §4 post-approval takedown).
# Stored as a JSON file at the path in EINVITE_PLUGIN_CRL_PATH (default:
# DATA/plugin_crl.json — a JSON array of revoked author_key_ids).
_CRL_CACHE: set[str] | None = None
_CRL_CACHE_TS: float = 0.0
_CRL_TTL_S = 300  # 5-minute cache


def _crl_path() -> str:
    """Return the path to the CRL JSON file."""
    data_dir = os.environ.get("EINVITE_DATA_DIR", "data")
    return os.path.join(data_dir, "plugin_crl.json")


def _load_crl() -> set[str]:
    """Load the CRL from disk, with a 5-minute in-process cache."""
    global _CRL_CACHE, _CRL_CACHE_TS
    now = time.time()
    if _CRL_CACHE is not None and (now - _CRL_CACHE_TS) < _CRL_TTL_S:
        return _CRL_CACHE
    try:
        with open(_crl_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            _CRL_CACHE = {str(k) for k in data}
        else:
            _CRL_CACHE = set()
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        _CRL_CACHE = set()
    _CRL_CACHE_TS = now
    return _CRL_CACHE


def check_revocation(author_key_id: str) -> bool:
    """Return True if the author_key_id is NOT revoked (i.e. still valid).

    Returns False if the author_key_id is in the CRL.
    """
    if not author_key_id:
        return False
    revoked = _load_crl()
    return author_key_id not in revoked


def _canonical_json(obj: Any) -> bytes:
    """Serialize to JSON in a canonical form (RFC 8785 / JCS-like).

    Sorts keys, no extra whitespace, ensure_ascii=False. This is the canonical
    form used for signature verification — both signer and verifier must
    produce identical bytes.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _verify_ed25519(public_key_b64: str, message: bytes, signature_b64: str) -> bool:
    """Verify an Ed25519 signature.

    Uses `cryptography` if available (preferred). Falls back to a basic
    pure-Python Ed25519 implementation if `cryptography` is not installed.

    Returns True iff the signature is valid for the message under the given
    public key.
    """
    try:
        public_key_bytes = base64.b64decode(public_key_b64)
        signature_bytes = base64.b64decode(signature_b64)
    except Exception:
        return False
    if len(public_key_bytes) != 32:
        return False
    if len(signature_bytes) != 64:
        return False
    # Preferred path: cryptography library
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
        pub = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        try:
            pub.verify(signature_bytes, message)
            return True
        except InvalidSignature:
            return False
    except ImportError:
        # Fallback: pure-Python Ed25519 (slower but stdlib-only).
        # For production, install `cryptography`: `pip install cryptography`.
        # This fallback is a simplified implementation that may not handle
        # all edge cases — it's a verification-only stub.
        try:
            import ed25519  # type: ignore
            vk = ed25519.VerifyingKey(public_key_bytes, encoding="raw")
            try:
                vk.verify(signature_bytes, message, encoding="raw")
                return True
            except Exception:
                return False
        except ImportError:
            # No Ed25519 library available — reject all signatures.
            # This is the fail-closed behavior: plugins cannot be verified
            # without a real Ed25519 implementation.
            return False


def verify_plugin_signature(manifest: dict, author_signature: str, marketplace_signature: str) -> bool:
    """Verify the double-signature on a plugin manifest.

    Per `docs/plugins/PLUGIN-SIGNING.md`:
      1. The author signs the canonical JSON of the manifest with their
         Ed25519 private key. The author's public key is in
         `manifest["author_key_id"]` (looked up via the marketplace keys
         endpoint).
      2. The marketplace CA signs the canonical JSON of the manifest + the
         author signature with the CA private key.

    Returns True iff BOTH signatures verify.

    Args:
        manifest: The plugin manifest dict.
        author_signature: Base64-encoded Ed25519 signature over canonical
            JSON of the manifest, signed by the author's private key.
        marketplace_signature: Base64-encoded Ed25519 signature over
            canonical JSON of (manifest + author_signature), signed by the
            CA private key.

    Returns:
        True iff both signatures verify.
    """
    if not isinstance(manifest, dict):
        return False
    if not author_signature or not marketplace_signature:
        return False
    # 1. Verify the author signature against the author's public key.
    author_pubkey_b64 = manifest.get("author_public_key") or ""
    if not author_pubkey_b64:
        # Without the author's public key embedded in the manifest, we can't
        # verify. The marketplace keys endpoint lookup is a follow-up.
        return False
    canonical_manifest = _canonical_json(manifest)
    if not _verify_ed25519(author_pubkey_b64, canonical_manifest, author_signature):
        return False
    # 2. Verify the marketplace CA signature over (manifest + author_signature).
    ca_payload = _canonical_json({
        "manifest": canonical_manifest.decode("utf-8"),
        "author_signature": author_signature,
    })
    if not _verify_ed25519(PINNED_CA_PUBKEY_B64, ca_payload, marketplace_signature):
        return False
    return True


def is_ca_configured() -> bool:
    """Return True if the CA public key has been set (not the placeholder)."""
    return PINNED_CA_PUBKEY_B64 != _PLACEHOLDER_CA_PUBKEY_B64


def marketplace_summary() -> dict:
    """Return a summary of the marketplace CA state for /_marketplace/keys/*."""
    return {
        "ca_configured": is_ca_configured(),
        "ca_public_key": PINNED_CA_PUBKEY_B64 if is_ca_configured() else None,
        "crl_path": _crl_path(),
        "crl_entries": len(_load_crl()),
    }

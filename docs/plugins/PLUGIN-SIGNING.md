# eInvite Plugin Double-Signing Specification (V54.6 / Phase 4a)

> **Status**: Phase 4a design document. Companion to `PLUGIN-SPEC.md` §2.1 (`signature` and `marketplace_signature` manifest fields).
> **Scope**: Defines the Ed25519 double-signing model (author key + marketplace CA key), the verification procedure at install and launch, key rotation, and the certificate revocation list (CRL) endpoint.
> **Threat model**: A plugin author's machine is compromised and their private key leaks. A malicious insider at the marketplace CA tries to sign an unreviewed plugin. A third-party CDN attempts to substitute a tampered bundle in transit. A revoked plugin attempts to run on an already-installed host.

---

## 1. Why double-signing

Single-signing (author key only) is insufficient because:

1. **Author key compromise** would silently allow any future plugin signed by the leaked key to install. Without a CA, there is no revocation authority and no review gate.
2. **Marketplace-only signing** (e.g. Apple's notarization alone) would allow the marketplace to mint plugins under any author's name, defeating authorship attribution.
3. **JetBrains-style unsigned plugins** are explicitly out of scope — the ROADMAP §7 4a design principle is "do it differently from JetBrains".

Double-signing means BOTH signatures must verify. The author signature proves the plugin came from the declared author. The marketplace signature proves the marketplace reviewed and approved that specific manifest+bundle combination. Removing or altering either signature refuses the install.

---

## 2. Cryptographic primitives

### 2.1 Signature algorithm

- **Ed25519** (RFC 8032). Chosen for: deterministic signatures (no nonce reuse risk), small signature size (64 bytes), small public key (32 bytes), constant-time implementation widely available (`libsodium`, `cryptography`, `tweetnacl`).
- **Hash**: Ed25519 is its own hash function internally (SHA-512); no separate hash step is needed.
- **Encoding**: lowercase hex (no `0x` prefix). Public keys are 32 bytes → 64 hex chars. Signatures are 64 bytes → 128 hex chars. The `author_key_id` (manifest §2.1) is SHA-256 of the Ed25519 public key (32 bytes → 64 hex chars).

### 2.2 Payload

The signed payload is the SHA-256 hash of the canonical manifest+bundle:

```
canonical_payload = sha256(
    "einvite-plugin-v1\n" +
    manifest_json_canonicalised + "\n" +
    bundle_sha256_hex + "\n" +
    bundle_size_bytes_ascii
)
```

Where:

- `manifest_json_canonicalised` is the manifest with `signature` and `marketplace_signature` set to empty objects `{}` (so the signature does not sign itself), UTF-8 encoded, with object keys sorted lexicographically, no insignificant whitespace, no BOM, no trailing newline. This is **JCS (JSON Canonicalization Scheme)** RFC 8785.
- `bundle_sha256_hex` is the lowercase-hex SHA-256 of the bundle tarball (`.tar.gz` of the plugin's `entrypoint` + assets, excluding the `manifest.json` itself).
- `bundle_size_bytes_ascii` is the decimal ASCII representation of the bundle size in bytes.

The 64-byte Ed25519 signature is over the raw bytes of `canonical_payload` (the 32-byte SHA-256 hash — Ed25519 signs the message directly; the canonical_payload string is the message).

### 2.3 Why sign the bundle hash too

Signing only the manifest would allow an attacker to swap the bundle (e.g. replace `index.html` with a malicious version) without invalidating the signature. Including `bundle_sha256_hex` and `bundle_size_bytes_ascii` in the signed payload binds the signature to a specific bundle.

---

## 3. Author signature

### 3.1 Key generation

The author generates an Ed25519 keypair locally. Recommended tooling: `python3 -c "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; k=Ed25519PrivateKey.generate(); print(k.private_bytes(...).hex(), k.public_key().public_bytes(...).hex())"`. Stdlib Python has no Ed25519 in `cryptography` is a third-party library but acceptable for the SDK CLI; the host-side verifier (in `validate_manifest.py`) uses stdlib only via `hashlib` for hashing — signature verification logic is implemented as a pure-Python Ed25519 verifier fallback (or, when available, uses `subprocess.run(["openssl", "pkeyutl", ...])` for Ed25519). The fallback is documented in `plugins/sdk/validate_manifest.py`.

The author keeps the private key secret (filesystem mode 0600, never committed to the plugin repo). The author publishes the public key (32 bytes, hex) when registering with the marketplace.

### 3.2 Signing procedure

```python
# Pseudocode — full implementation in plugins/sdk/validate_manifest.py
import hashlib, json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

def sign_manifest(manifest: dict, bundle_path: str, private_key: Ed25519PrivateKey) -> dict:
    canonical = canonicalise(manifest)  # JCS, with signature+marketplace_signature = {}
    bundle_bytes = open(bundle_path, "rb").read()
    bundle_sha = hashlib.sha256(bundle_bytes).hexdigest()
    message = f"einvite-plugin-v1\n{canonical}\n{bundle_sha}\n{len(bundle_bytes)}\n".encode()
    sig = private_key.sign(message).hex()
    return {
        "algorithm": "ed25519",
        "public_key": private_key.public_key().public_bytes_raw().hex(),
        "sig": sig,
        "signed_payload": "manifest+bundle",
        "signed_at": int(time.time())
    }
```

### 3.3 Author key registration

The author registers their public key with the marketplace:

1. Author signs a registration payload `{ "vendor_id": "...", "public_key": "...", "registered_at": N, "email": "..." }` with the corresponding private key.
2. The marketplace verifies the self-signature and stores the public key indexed by `author_key_id = sha256(public_key_bytes).hex()`.
3. The public key is published at `GET /_marketplace/keys/{author_key_id}` (returns the public key hex + registration payload + marketplace CA counter-signature on the registration).

This makes author keys publicly auditable: any host can fetch the author's public key by `author_key_id` and verify the author signature independently of the marketplace.

---

## 4. Marketplace CA signature

### 4.1 The marketplace CA key

The eInvite marketplace holds a single root CA Ed25519 keypair. The private key is stored in a hardware security module (HSM) or, at minimum, on an air-gapped signing workstation. The public key is hardcoded into the host platform binary (in `src/python/plugin_marketplace_ca.py` — to be added in Phase 4a follow-up).

The host's pinned CA public key is the trust anchor. A new CA key requires a platform release (a new `BUILD_INFO.ca_key_fingerprint` value).

### 4.2 Approval flow

1. Author submits the manifest+bundle to the marketplace via `POST /_marketplace/plugins/submit`.
2. The marketplace runs the automated moderation pipeline (`MODERATION-PIPELINE.md` §3).
3. If automated checks pass, the submission enters the human-review queue (`MODERATION-PIPELINE.md` §4).
4. On approval, a marketplace maintainer triggers `POST /_marketplace/plugins/{id}/approve` from the signing workstation.
5. The marketplace CA signs the canonical payload (same `canonical_payload` string the author signed — see §2.2) and returns the `marketplace_signature` block.
6. The marketplace publishes the doubly-signed manifest at `GET /_marketplace/plugins/{id}/manifest.json`.

### 4.3 Approval subset

The marketplace may approve a subset of the author's declared permissions (see `PLUGIN-SPEC.md` §3.4). The `marketplace_signature` block therefore includes an `approved_permissions` field listing the approved permission strings. The host intersects this with the manifest's `permissions[]` to derive the final approved set.

```json
"marketplace_signature": {
  "algorithm": "ed25519",
  "public_key": "ee1a0000000000000000000000000000000000000000000000000000000000e1",
  "sig": "9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e",
  "signed_payload": "manifest",
  "approved_permissions": ["invitation:{current}:rsvp:read"],
  "approved_extension_points": ["content.block"],
  "signed_at": 1789300000,
  "expires_at": 1820900000,
  "reviewer": "marketplace-maintainer-1",
  "review_ticket": "MR-2026-001234"
}
```

The CA signature is over the canonical manifest PLUS the `approved_permissions` + `approved_extension_points` lists (so a maintainer cannot retroactively change what was approved without invalidating the signature).

### 4.4 Expiration

The `marketplace_signature.expires_at` field is a hard deadline. The marketplace sets it to `signed_at + 365 days` by default (or shorter for plugins in beta). After expiry:

- New installs are refused with `{"error": "marketplace_signature_expired", "expires_at": ...}`.
- Already-installed plugins continue to run, but the host surfaces a yellow banner ("Plugin {name} marketplace approval expired on {date}. Re-install from the marketplace to renew.").
- The author can re-submit; the marketplace re-runs the moderation pipeline and re-signs with a fresh `expires_at`.

Author signatures do not expire (an author's signature on a specific bundle is permanent — what changes is whether the marketplace still vouches for it).

---

## 5. Verification on install

The host runs the following verification on every install and on every subsequent launch:

### 5.1 Install-time verification

```
1. Fetch the doubly-signed manifest from the marketplace.
2. Verify the marketplace CA signature:
   a. Look up the host's pinned CA public key (hardcoded in plugin_marketplace_ca.py).
   b. Recompute the canonical_payload string (§2.2 — same algorithm the author used).
   c. Append the approved_permissions and approved_extension_points lists to the payload (per §4.3).
   d. Verify the Ed25519 signature of that payload against the pinned CA public key.
   e. If verification fails → refuse install with {"error": "marketplace_signature_invalid"}.
3. Verify the marketplace signature has not expired (signed_at <= now < expires_at).
4. Verify the author signature:
   a. Fetch the author's public key from GET /_marketplace/keys/{author_key_id}.
   b. Verify the marketplace CA counter-signature on the author key registration (§3.3).
   c. Recompute the canonical_payload string and verify the Ed25519 signature.
   d. If verification fails → refuse install with {"error": "author_signature_invalid"}.
5. Verify the bundle hash:
   a. Download the bundle.
   b. Compute sha256(bundle) and compare to the value embedded in the canonical_payload.
   c. If mismatch → refuse install with {"error": "bundle_hash_mismatch"}.
6. Check the CRL (§6): fetch GET /_marketplace/crl.json and confirm neither author_key_id nor the plugin's marketplace_signature.sig appears in the revocation list.
7. Persist the doubly-signed manifest + bundle hash + approved_permissions in plugin_installations_v48.
```

### 5.2 Launch-time verification

On every host launch (and every 24 hours thereafter), the host:

1. Recomputes the bundle hash from the locally-cached bundle.
2. Verifies the cached author signature and marketplace signature against the cached manifest+bundle hash.
3. Re-fetches the CRL (cached for 24h) and confirms the plugin's signatures are still in good standing.
4. If any check fails, the host disables the plugin and surfaces a takedown notice (see `MODERATION-PIPELINE.md` §4.3).

### 5.3 Refusal of unsigned or single-signed plugins

The host hard-refuses:

- Unsigned plugins (no `signature` block).
- Single-signed plugins (only `signature` present, no `marketplace_signature`, or `marketplace_signature.sig` is all zeros / empty).
- Plugins where the marketplace CA signature was produced by a key that does not match the host's pinned CA public key (i.e. someone tried to mint their own "marketplace").

There is no developer-mode bypass in production (`EINVITE_ALLOW_UNSIGNED_PLUGINS=1` is rejected by `production_preflight` in the same pattern as `EINVITE_ALLOW_NO_SCANNER=1` — see V54 worklog). Dev-only unsigned plugins are allowed in the existing V48 manifest-registration UI (`src/js/plugin-platform-v48.js:registerManifest()`) and are confined to a separate "Development plugins" section that cannot reach the marketplace listing.

---

## 6. Revocation — Certificate Revocation List (CRL)

### 6.1 CRL endpoint

The marketplace exposes `GET /_marketplace/crl.json`:

```json
{
  "schema_version": 1,
  "ca_public_key": "ee1a0000000000000000000000000000000000000000000000000000000000e1",
  "crl_seq": 87,
  "generated_at": 1789300000,
  "next_update_at": 1789386400,
  "revoked_author_keys": [
    {
      "author_key_id": "9f1a8d3e2b5c4f6a7e8d9c0b1a2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e",
      "revoked_at": 1789200000,
      "reason": "key_compromise"
    }
  ],
  "revoked_marketplace_signatures": [
    {
      "plugin_id": "com.example.bad-plugin",
      "version": "1.2.0",
      "marketplace_sig_sha256": "abcdef...",
      "revoked_at": 1789250000,
      "reason": "moderation_takedown"
    }
  ],
  "ca_signature": {
    "algorithm": "ed25519",
    "public_key": "ee1a0000000000000000000000000000000000000000000000000000000000e1",
    "sig": "..."
  }
}
```

The CRL itself is signed by the marketplace CA. The host verifies the CRL's CA signature against the pinned CA public key before consulting it.

### 6.2 Revocation reasons

| Reason | Effect on installed plugins |
|---|---|
| `key_compromise` (author key) | Disable every plugin signed by that author key. Surface a takedown notice. |
| `moderation_takedown` (specific marketplace signature) | Disable the specific plugin+version. Surface a takedown notice with the moderator's reason. |
| `author_request` (author-initiated) | Disable the plugin. Surface a notice ("The author has withdrawn this plugin from the marketplace."). |
| `supercession` (a newer version supersedes an older one) | Do NOT auto-disable. Surface a notice ("A newer version is available."). |

### 6.3 Takedown notice

When the host detects a plugin in the CRL, it:

1. Marks the plugin as `disabled: revoked` in `plugin_installations_v48`.
2. Renders a takedown notice in the host dashboard:

   > ⚠️ Plugin "Confetti animation" v1.0.0 has been disabled.
   >
   > Reason: moderation_takedown
   > Revoked at: 2026-09-12 14:32 UTC
   > Marketplace reference: MR-2026-001234
   >
   > The plugin cannot be re-enabled. Its sandbox iframe will not load. Existing plugin configuration data is preserved for export. Uninstall the plugin to clear its sandbox storage.
   >
   > ប្រអប់កម្មវិធី "អានីម៉េសិនផ្កាយរត់" កំណែ 1.0.0 ត្រូវបានបិទ។ សូមពិនិត្យមើលហេតុផលខាងលើ។

3. Sends a `plugin.takedown` audit event with actor=`marketplace_crl`, target=plugin_id, reason, severity=`high`.

### 6.4 CRL freshness

The host fetches the CRL:

- On launch.
- Every 24 hours.
- On-demand when a plugin install is attempted (to avoid the race where a plugin was revoked between CRL fetches).

If the CRL fetch fails (network error), the host:

- Uses the last-known-good CRL (cached locally) for up to 7 days.
- After 7 days, refuses new plugin installs (a stale CRL is treated as untrusted) but continues running already-installed plugins (which were verified at install time).
- Surfaces a yellow banner in the dashboard ("Marketplace CRL unreachable for {N} days. New plugin installs are suspended until the marketplace is reachable.").

---

## 7. Key rotation

### 7.1 Author key rotation

An author may rotate their Ed25519 keypair at any time:

1. Generate a new keypair locally.
2. Sign a `{ "author_key_rotation": { "old_key_id": "...", "new_key_id": "...", "new_public_key": "...", "rotated_at": N } }` payload with BOTH the old and the new private key (proving the rotation was authorized by the old key holder).
3. Submit to `POST /_marketplace/authors/rotate-key`.
4. The marketplace CA counter-signs the rotation record.
5. The marketplace publishes the rotation chain at `GET /_marketplace/keys/{new_author_key_id}/rotation`.

Hosts treat the rotation chain as authoritative: any plugin signed by the OLD key remains valid (the old key is not revoked — it is "superseded"). Plugins signed AFTER the rotation cutoff MUST use the new key.

If the old key is later revoked with `reason: key_compromise`, plugins signed by the old key BEFORE the rotation cutoff remain valid (because the rotation record proves the author controlled the old key at rotation time — the compromise must have happened after).

### 7.2 Marketplace CA key rotation

The marketplace CA key is rotated only via a platform release:

1. The new CA keypair is generated on the signing workstation.
2. A platform release (V55+) ships with BOTH the old and new CA public keys pinned (overlap window: 6 months).
3. During the overlap window, the marketplace re-signs every approved plugin with the new CA key.
4. After the overlap window, a subsequent platform release (V57+) ships with ONLY the new CA public key pinned. Plugins not yet re-signed by the new CA key are auto-disabled (their `marketplace_signature.public_key` no longer matches the pinned CA).

The rotation is announced 90 days in advance via the marketplace dashboard + the `marketplace_signature.expires_at` field is shortened to the rotation cutoff on all newly-signed plugins (so authors have a forcing function to re-sign).

### 7.3 Host-side key pinning

The host pins the marketplace CA public key(s) in `src/python/plugin_marketplace_ca.py` (to be added in Phase 4a code follow-up):

```python
# plugin_marketplace_ca.py
PINNED_CA_KEYS = {
    # active CA key (Phase 4a launch)
    "ee1a0000000000000000000000000000000000000000000000000000000000e1": {
        "active_since": "2026-09-12",
        "superseded_at": None,
    },
    # future rotations appended below
}
```

A new pinned key requires a `BUILD_INFO.ca_key_fingerprint` bump + a `VERSION_HISTORY.md` entry.

---

## 8. Acceptance criteria

- Both signatures (author + marketplace) are required at install and at launch. Missing either refuses the plugin.
- The CRL endpoint is signed by the marketplace CA and cached by the host for 24 hours.
- Author key rotation is supported via a dual-signed rotation record.
- Marketplace CA rotation requires a platform release with an overlap window.
- The verification code lives in `plugins/sdk/validate_manifest.py` (stdlib-only) and is the single source of truth used by both the marketplace submission tool and the host install path.

---

## 9. References

- `docs/plugins/PLUGIN-SPEC.md` §2.1 — manifest fields `signature` and `marketplace_signature`.
- `docs/plugins/PLUGIN-SANDBOX.md` — sandboxed execution (every capability is gated by the manifest's permissions, which are gated by the marketplace's approval subset).
- `docs/plugins/MODERATION-PIPELINE.md` — moderation pipeline (the human review step is the precondition for marketplace signing).
- `plugins/sdk/validate_manifest.py` — stdlib-only signature verifier (fallback path uses `subprocess` to `openssl`; primary path uses pure-Python Ed25519).
- `docs/ai/JIT-ELEVATION.md` §3 (cross-instance revocation) — same pattern: a server-side table is the source of truth, hosts cache and refresh on a schedule.
- RFC 8032 — Ed25519.
- RFC 8785 — JSON Canonicalization Scheme.

*Last updated: Phase 4a (V54.6).*

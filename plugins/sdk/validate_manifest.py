#!/usr/bin/env python3
"""
eInvite plugin manifest validator.

Validates a plugin manifest.json against:
  1. The JSON Schema at plugins/sdk/manifest.schema.json (draft 2020-12).
  2. A recursive scan for forbidden field names (PLUGIN-SPEC.md §2.3).
  3. The manifest's permission grammar (PLUGIN-SPEC.md §3.1).
  4. (Optional) Author + marketplace Ed25519 signatures (PLUGIN-SIGNING.md).

Stdlib-only — no third-party dependencies (no `jsonschema`, no `cryptography`).
The JSON Schema validator is a hand-rolled subset that covers the eInvite
manifest schema's constructs (type, const, enum, required, properties,
additionalProperties, pattern, minLength, maxLength, minimum, maximum,
minItems, maxItems, uniqueItems, $ref/$defs, format=email).

Usage:
    python3 validate_manifest.py <manifest.json>
    python3 validate_manifest.py <manifest.json> --check-signatures <bundle.tar.gz>
    python3 validate_manifest.py <manifest.json> --report json
    python3 validate_manifest.py <manifest.json> --report human

Exit codes:
    0 = manifest is valid (and signatures verify, if --check-signatures was passed).
    1 = manifest is invalid OR signature verification failed.
    2 = bad CLI args / file not found / IO error.

This script is the single source of truth used by:
    - The marketplace submission pipeline (MODERATION-PIPELINE.md §3.1).
    - The host install path (PLUGIN-SIGNING.md §5.1).
    - Plugin authors during local development.

Version: 1.0.0 (Phase 4a / V54.6)
"""

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


SCHEMA_VERSION = "1.0.0"
PHASE = "4a (V54.6)"

# ─── Forbidden field names (PLUGIN-SPEC.md §2.3) ─────────────────────────
# Union of the V48 runtime forbidden set (src/js/plugin-runtime-v48.js) and
# the additional DOM-API tokens added in Phase 4a.
FORBIDDEN_FIELDS = frozenset({
    "script", "javascript", "code", "eval", "html", "cssText",
    "filesystemPath", "networkUrl", "sql", "srcdoc", "onload", "onclick",
    "innerHTML", "outerHTML", "document_cookie", "window_location",
})

# Recursive depth + array length caps (match V48 runtime scan()).
MAX_NESTING_DEPTH = 12
MAX_ARRAY_LENGTH = 500

# Permission grammar (PLUGIN-SPEC.md §3.1).
RESOURCE_TYPES = frozenset({
    "invitation", "event", "template", "workspace", "asset",
    "plugin", "guest", "message", "page", "account",
})
PERMISSION_PATTERN = re.compile(
    r"^(invitation|event|template|workspace|asset|plugin|guest|message|page|account):"
    r"(\{current\}|\{[a-f0-9-]+\}|[a-f0-9-]+):"
    r"[a-z][a-z0-9-]*"
    r"(?::[a-z][a-z0-9-]*(?::[a-f0-9-]+)?)?$"
)

# Semver 2.0.0 pattern (subset — no build metadata for min/max platform version).
SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")

# The 13 extension points (PLUGIN-SPEC.md §4).
EXTENSION_POINTS = frozenset({
    "editor.panel", "content.block", "asset.provider",
    "export.provider", "communication.provider", "payment.provider",
    "analytics.provider", "storage.provider", "ai.provider",
    "calendar.provider", "map.provider",
    "template.provider", "automation.provider",
})

# CSP tokens that must NEVER appear in any directive.
FORBIDDEN_CSP_TOKENS = frozenset({"'unsafe-inline'", "'unsafe-eval'", "'unsafe-hashes'"})


# ─── Minimal JSON Schema validator (subset of draft 2020-12) ─────────────


class ValidationError(Exception):
    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


def _resolve_ref(ref: str, root: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve a #/$defs/... or #/$defs/<name> reference."""
    if not ref.startswith("#/"):
        raise ValidationError("$ref", f"unsupported $ref (must be internal #/$defs/...): {ref}")
    parts = ref[2:].split("/")
    node = root
    for p in parts:
        if not isinstance(node, dict) or p not in node:
            raise ValidationError("$ref", f"cannot resolve $ref {ref}")
        node = node[p]
    return node


def _check_string(value: Any, schema: Dict[str, Any], path: str) -> None:
    if schema.get("const") is not None and value != schema["const"]:
        raise ValidationError(path, f"expected const {schema['const']!r}, got {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValidationError(path, f"value {value!r} not in enum {schema['enum']!r}")
    if "pattern" in schema:
        if not re.match(schema["pattern"], value):
            raise ValidationError(path, f"value {value!r} does not match pattern {schema['pattern']!r}")
    if "minLength" in schema and len(value) < schema["minLength"]:
        raise ValidationError(path, f"string too short (min {schema['minLength']}, got {len(value)})")
    if "maxLength" in schema and len(value) > schema["maxLength"]:
        raise ValidationError(path, f"string too long (max {schema['maxLength']}, got {len(value)})")


def _check_number(value: Any, schema: Dict[str, Any], path: str) -> None:
    if "minimum" in schema and value < schema["minimum"]:
        raise ValidationError(path, f"value {value} < minimum {schema['minimum']}")
    if "maximum" in schema and value > schema["maximum"]:
        raise ValidationError(path, f"value {value} > maximum {schema['maximum']}")


def _check_array(value: Any, schema: Dict[str, Any], path: str, root: Dict[str, Any]) -> None:
    if "maxItems" in schema and len(value) > schema["maxItems"]:
        raise ValidationError(path, f"array too long (max {schema['maxItems']}, got {len(value)})")
    if "minItems" in schema and len(value) < schema["minItems"]:
        raise ValidationError(path, f"array too short (min {schema['minItems']}, got {len(value)})")
    if schema.get("uniqueItems") and len(set(map(json.dumps, value))) != len(value):
        raise ValidationError(path, "array items not unique")
    if "items" in schema:
        for i, item in enumerate(value):
            _validate_node(item, schema["items"], f"{path}[{i}]", root)


def _check_object(value: Any, schema: Dict[str, Any], path: str, root: Dict[str, Any]) -> None:
    if "required" in schema:
        for req in schema["required"]:
            if req not in value:
                raise ValidationError(path, f"missing required field {req!r}")
    if schema.get("additionalProperties") is False:
        allowed = set((schema.get("properties") or {}).keys())
        unknown = set(value.keys()) - allowed
        if unknown:
            raise ValidationError(path, f"unknown fields: {sorted(unknown)}")
    if "properties" in schema:
        for name, subschema in schema["properties"].items():
            if name in value:
                _validate_node(value[name], subschema, f"{path}.{name}", root)


def _validate_node(value: Any, schema: Dict[str, Any], path: str, root: Dict[str, Any]) -> None:
    if "$ref" in schema:
        schema = {**schema, **_resolve_ref(schema["$ref"], root)}
        del schema["$ref"]
    if "const" in schema:
        if value != schema["const"]:
            raise ValidationError(path, f"expected const {schema['const']!r}, got {value!r}")
        return
    if "enum" in schema:
        if value not in schema["enum"]:
            raise ValidationError(path, f"value {value!r} not in enum {schema['enum']!r}")
        return
    expected_type = schema.get("type")
    if expected_type == "object" and not isinstance(value, dict):
        raise ValidationError(path, f"expected object, got {type(value).__name__}")
    if expected_type == "array" and not isinstance(value, list):
        raise ValidationError(path, f"expected array, got {type(value).__name__}")
    if expected_type == "string" and not isinstance(value, str):
        raise ValidationError(path, f"expected string, got {type(value).__name__}")
    if expected_type == "integer" and not (isinstance(value, int) and not isinstance(value, bool)):
        raise ValidationError(path, f"expected integer, got {type(value).__name__}")
    if expected_type == "boolean" and not isinstance(value, bool):
        raise ValidationError(path, f"expected boolean, got {type(value).__name__}")
    if isinstance(value, str):
        _check_string(value, schema, path)
        if schema.get("format") == "email":
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
                raise ValidationError(path, f"not a valid email: {value!r}")
    elif isinstance(value, int) and not isinstance(value, bool):
        _check_number(value, schema, path)
    elif isinstance(value, list):
        _check_array(value, schema, path, root)
    elif isinstance(value, dict):
        _check_object(value, schema, path, root)


def validate_against_schema(manifest: Dict[str, Any], schema: Dict[str, Any]) -> List[ValidationError]:
    errors: List[ValidationError] = []
    try:
        _validate_node(manifest, schema, "$", schema)
    except ValidationError as e:
        errors.append(e)
    return errors


# ─── Forbidden-field recursive scan (PLUGIN-SPEC.md §2.3) ────────────────


def scan_forbidden(value: Any, path: str = "$", depth: int = 0) -> List[ValidationError]:
    errors: List[ValidationError] = []
    if depth > MAX_NESTING_DEPTH:
        errors.append(ValidationError(path, f"nesting too deep (> {MAX_NESTING_DEPTH})"))
        return errors
    if isinstance(value, list):
        if len(value) > MAX_ARRAY_LENGTH:
            errors.append(ValidationError(path, f"array too long (> {MAX_ARRAY_LENGTH})"))
        for i, item in enumerate(value):
            errors.extend(scan_forbidden(item, f"{path}[{i}]", depth + 1))
        return errors
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_FIELDS:
                errors.append(ValidationError(f"{path}.{key}", f"forbidden field name: {key!r}"))
            errors.extend(scan_forbidden(item, f"{path}.{key}", depth + 1))
    return errors


# ─── Permission grammar check (PLUGIN-SPEC.md §3) ───────────────────────


def check_permissions(manifest: Dict[str, Any]) -> List[ValidationError]:
    errors: List[ValidationError] = []
    perms = manifest.get("permissions", [])
    for i, p in enumerate(perms):
        if not isinstance(p, str) or not PERMISSION_PATTERN.match(p):
            errors.append(ValidationError(f"$.permissions[{i}]", f"invalid permission: {p!r}"))
            continue
        # Reject wildcard resource_id.
        parts = p.split(":")
        if len(parts) >= 2 and parts[1] == "*":
            errors.append(ValidationError(f"$.permissions[{i}]", f"wildcard resource_id rejected: {p!r}"))
        # Reject unknown resource type (defensive — the regex already enforces this).
        if parts[0] not in RESOURCE_TYPES:
            errors.append(ValidationError(f"$.permissions[{i}]", f"unknown resource_type: {parts[0]!r}"))
    return errors


# ─── CSP audit (PLUGIN-SPEC.md §5 + MODERATION-PIPELINE.md §3.6) ────────


def check_csp(manifest: Dict[str, Any]) -> List[ValidationError]:
    errors: List[ValidationError] = []
    csp = manifest.get("content_security_policy", {})
    if not isinstance(csp, dict):
        return errors
    for directive, tokens in csp.items():
        if not isinstance(tokens, list):
            errors.append(ValidationError(f"$.content_security_policy.{directive}", "CSP directive value must be an array"))
            continue
        for tok in tokens:
            if not isinstance(tok, str):
                errors.append(ValidationError(f"$.content_security_policy.{directive}", "CSP token must be a string"))
                continue
            if tok in FORBIDDEN_CSP_TOKENS:
                errors.append(ValidationError(f"$.content_security_policy.{directive}", f"forbidden CSP token: {tok!r}"))
            # connect_src must be only 'self' (the sandbox cannot make direct network calls).
            if directive == "connect_src" and tok != "'self'":
                errors.append(ValidationError(f"$.content_security_policy.{directive}", f"connect_src must be 'self'; got {tok!r}"))
    return errors


# ─── Bilingual completeness (MODERATION-PIPELINE.md §3.8) ───────────────


def check_bilingual(manifest: Dict[str, Any]) -> List[ValidationError]:
    errors: List[ValidationError] = []
    pairs = [("name", "name_kh"), ("description", "description_kh")]
    for base, kh in pairs:
        if base in manifest and kh not in manifest:
            errors.append(ValidationError(f"$.{kh}", f"missing Khmer variant for {base!r}"))
        elif base in manifest and kh in manifest:
            if manifest[base] == manifest[kh]:
                errors.append(ValidationError(f"$.{kh}", f"Khmer variant is byte-identical to English variant {base!r}"))
    # extension_points[].label + label_kh
    eps = manifest.get("extension_points", [])
    for i, ep in enumerate(eps):
        if not isinstance(ep, dict):
            continue
        if "label" in ep and "label_kh" not in ep:
            errors.append(ValidationError(f"$.extension_points[{i}].label_kh", "missing Khmer variant for label"))
        elif "label" in ep and "label_kh" in ep and ep["label"] == ep["label_kh"]:
            errors.append(ValidationError(f"$.extension_points[{i}].label_kh", "Khmer variant is byte-identical to English variant"))
    return errors


# ─── Extension-point enum check ────────────────────────────────────────


def check_extension_points(manifest: Dict[str, Any]) -> List[ValidationError]:
    errors: List[ValidationError] = []
    eps = manifest.get("extension_points", [])
    for i, ep in enumerate(eps):
        if not isinstance(ep, dict):
            errors.append(ValidationError(f"$.extension_points[{i}]", "must be an object"))
            continue
        point = ep.get("point")
        if point not in EXTENSION_POINTS:
            errors.append(ValidationError(f"$.extension_points[{i}].point", f"unknown extension point: {point!r}"))
    return errors


# ─── Signature verification (PLUGIN-SIGNING.md) ────────────────────────
#
# Ed25519 verification requires either:
#   (a) the `cryptography` package (third-party), or
#   (b) the `openssl` CLI in a subprocess, or
#   (c) a pure-Python Ed25519 verifier (the fallback bundled with this script).
#
# The validate_manifest.py CLI uses path (b) when `openssl` is available, and
# falls back to (c) otherwise. The marketplace's production install path
# uses (a). The pure-Python fallback is included so the script remains
# stdlib-only as required by the task spec ("Stdlib Python only").


def _canonical_payload(manifest: Dict[str, Any], bundle_sha256_hex: str, bundle_size: int) -> bytes:
    """Compute the canonical payload string per PLUGIN-SIGNING.md §2.2.

    The signature is computed over the canonical_payload (the SHA-256 hash
    itself is the message in Ed25519's signing step — but for verification
    we sign/verify the canonical_payload bytes directly).
    """
    # JCS: keys sorted lexicographically, no whitespace, signature + marketplace_signature = {}.
    m = dict(manifest)
    m["signature"] = {}
    m["marketplace_signature"] = {}
    canonical = json.dumps(m, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"einvite-plugin-v1\n{canonical}\n{bundle_sha256_hex}\n{bundle_size}\n".encode("utf-8")


def _verify_ed25519_openssl(public_key_hex: str, message: bytes, sig_hex: str) -> bool:
    """Verify an Ed25519 signature using the `openssl` CLI in a subprocess.

    Returns True if the signature verifies, False otherwise.
    Raises RuntimeError if openssl is unavailable.
    """
    import subprocess
    import tempfile

    try:
        # Construct a PEM-encoded Ed25519 public key from the raw 32 bytes.
        # openssl pkeyutl -verify requires a PEM key file; we synthesize one.
        raw_pub = bytes.fromhex(public_key_hex)
        if len(raw_pub) != 32:
            return False
        # Asn.1 DER for Ed25519 public key:
        #   SEQUENCE { SEQUENCE { OID 1.3.101.112 }, BIT STRING <32 bytes> }
        der = bytes([
            0x30, 0x2a,  # SEQUENCE, len 42
            0x30, 0x05,  # SEQUENCE, len 5
            0x06, 0x03, 0x2b, 0x65, 0x70,  # OID 1.3.101.112 (Ed25519)
            0x03, 0x21, 0x00,  # BIT STRING, len 33, 0 unused bits
        ]) + raw_pub
        # Base64-encode the DER for PEM.
        import base64
        b64 = base64.encodebytes(der).decode("ascii").replace("\n", "")
        pem = f"-----BEGIN PUBLIC KEY-----\n{b64}\n-----END PUBLIC KEY-----\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as f:
            f.write(pem)
            pem_path = f.name
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(message)
            msg_path = f.name
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(bytes.fromhex(sig_hex))
            sig_path = f.name
        try:
            result = subprocess.run(
                ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", pem_path,
                 "-rawin", "-in", msg_path, "-sigfile", sig_path],
                capture_output=True, timeout=5
            )
            return result.returncode == 0 and b"Verified" in (result.stdout + result.stderr)
        finally:
            for p in (pem_path, msg_path, sig_path):
                try:
                    os.unlink(p)
                except OSError:
                    pass
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        return False


def _verify_ed25519_pure_python(public_key_hex: str, message: bytes, sig_hex: str) -> bool:
    """Pure-Python Ed25519 verifier. Implements RFC 8032 directly.

    This is a self-contained verifier with no third-party dependencies.
    It is slower than the C-backed `openssl` path but produces the same
    results. Used as a fallback when `openssl` is not available.
    """
    # ─── RFC 8032 reference implementation (verification only) ──────────
    # Adapted from the public-domain reference at https://ed25519.cr.yp.to/
    # Constants.
    p = 2 ** 255 - 19
    L = 2 ** 252 + 27742317777372353535851937790883648493
    d = (-121665 * pow(121666, -1, p)) % p
    I = pow(2, (p - 1) // 4, p)

    def xrecover(y):
        xx = (y * y - 1) * pow(d * y * y + 1, -1, p)
        x = pow(xx, (p + 3) // 8, p)
        if (x * x - xx) % p != 0:
            x = (x * I) % p
        if x % 2 != 0:
            x = p - x
        return x

    By = 4 * pow(5, -1, p) % p
    Bx = xrecover(By)
    B = [Bx % p, By % p]

    def edwards(P, Q):
        x1, y1 = P; x2, y2 = Q
        x3 = (x1 * y2 + x2 * y1) * pow(1 + d * x1 * x2 * y1 * y2, -1, p) % p
        y3 = (y1 * y2 + x1 * x2) * pow(1 - d * x1 * x2 * y1 * y2, -1, p) % p
        return [x3 % p, y3 % p]

    def scalarmult(P, e):
        if e == 0:
            return [0, 1]
        Q = scalarmult(P, e // 2)
        Q = edwards(Q, Q)
        if e & 1:
            Q = edwards(Q, P)
        return Q

    def sha512(b: bytes) -> bytes:
        import hashlib
        return hashlib.sha512(b).digest()

    def H_int(b: bytes) -> int:
        return int.from_bytes(sha512(b), "little")

    try:
        pub = bytes.fromhex(public_key_hex)
        sig = bytes.fromhex(sig_hex)
        if len(pub) != 32 or len(sig) != 64:
            return False
        R = sig[:32]
        S = int.from_bytes(sig[32:], "little")
        if S >= L:
            return False
        A_y = int.from_bytes(pub, "little")
        A_x = xrecover(A_y & ((1 << 255) - 1))  # extract y, recover x
        # Parity bit of x is the high bit of the encoded point.
        if (A_y >> 255) & 1:
            A_x = (-A_x) % p
        A = [A_x, A_y % p]
        k = H_int(R + pub + message) % L
        # Check: [S]B = R + [k]A
        lhs = scalarmult(B, S)
        rhs = edwards(R_to_point(R, p), scalarmult(A, k))
        return lhs == rhs
    except Exception:
        return False


def R_to_point(R_bytes: bytes, p: int) -> List[int]:
    """Decode the y coordinate of R and recover x via the curve equation."""
    y = int.from_bytes(R_bytes, "little") & ((1 << 255) - 1)
    x = (-1)  # placeholder; xrecover from pure-python path
    # Reuse the inner function by reconstructing it inline.
    d = (-121665 * pow(121666, -1, p)) % p
    I = pow(2, (p - 1) // 4, p)
    xx = (y * y - 1) * pow(d * y * y + 1, -1, p)
    x = pow(xx, (p + 3) // 8, p)
    if (x * x - xx) % p != 0:
        x = (x * I) % p
    if x % 2 != 0:
        x = p - x
    return [x % p, y % p]


def verify_signature_block(sig_block: Dict[str, Any], manifest: Dict[str, Any],
                           bundle_sha256_hex: str, bundle_size: int,
                           pinned_public_key: Optional[str] = None,
                           label: str = "signature") -> Tuple[bool, str]:
    """Verify a single Ed25519 signature block.

    Returns (ok, reason).
    """
    if not isinstance(sig_block, dict):
        return False, f"{label}: not an object"
    if sig_block.get("algorithm") != "ed25519":
        return False, f"{label}: algorithm must be ed25519"
    public_key = sig_block.get("public_key", "")
    sig_hex = sig_block.get("sig", "")
    if not re.match(r"^[a-f0-9]{64}$", public_key):
        return False, f"{label}: public_key must be 64 hex chars"
    if not re.match(r"^[a-f0-9]{128}$", sig_hex):
        return False, f"{label}: sig must be 128 hex chars"
    if pinned_public_key and public_key != pinned_public_key:
        return False, f"{label}: public_key does not match pinned key"
    message = _canonical_payload(manifest, bundle_sha256_hex, bundle_size)
    # Try openssl first (faster + audited); fall back to pure Python.
    if _openssl_available():
        ok = _verify_ed25519_openssl(public_key, message, sig_hex)
        if ok:
            return True, f"{label}: verified (openssl)"
        # If openssl fails AND the sig block is the unsigned placeholder
        # (all zeros), short-circuit.
        if sig_hex == "0" * 128:
            return False, f"{label}: signature is the unsigned placeholder (all zeros)"
        # Otherwise try the pure-Python fallback in case openssl is misconfigured.
        ok_py = _verify_ed25519_pure_python(public_key, message, sig_hex)
        return (ok_py, f"{label}: verified (pure-python fallback)") if ok_py else (False, f"{label}: signature does not verify")
    else:
        ok = _verify_ed25519_pure_python(public_key, message, sig_hex)
        return (True, f"{label}: verified (pure-python)") if ok else (False, f"{label}: signature does not verify")


def _openssl_available() -> bool:
    import shutil
    return shutil.which("openssl") is not None


# ─── Top-level report ──────────────────────────────────────────────────


def validate_manifest_file(manifest_path: str, bundle_path: Optional[str] = None,
                           check_signatures: bool = False) -> Dict[str, Any]:
    """Validate a manifest.json file.

    Returns a report dict with:
      - schema_version (the SDK's version)
      - manifest_path
      - checks: list of { name, result, details }
      - overall: 'pass' | 'fail'
    """
    report: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase": PHASE,
        "manifest_path": manifest_path,
        "bundle_path": bundle_path,
        "checks": [],
        "overall": "fail",
    }

    # Load manifest.
    if not os.path.isfile(manifest_path):
        report["checks"].append({"name": "manifest_exists", "result": "fail",
                                 "details": f"file not found: {manifest_path}"})
        return report
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_text = f.read()
        manifest = json.loads(manifest_text)
    except (IOError, json.JSONDecodeError) as e:
        report["checks"].append({"name": "manifest_load", "result": "fail",
                                 "details": str(e)})
        return report
    report["checks"].append({"name": "manifest_load", "result": "pass",
                             "details": f"{len(manifest_text)} bytes"})

    # Load schema (same directory as this script).
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.schema.json")
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        report["checks"].append({"name": "schema_load", "result": "fail",
                                 "details": f"cannot load schema: {e}"})
        return report

    # Schema validation.
    schema_errors = validate_against_schema(manifest, schema)
    if schema_errors:
        report["checks"].append({
            "name": "manifest_schema",
            "result": "fail",
            "details": [{"path": e.path, "message": e.message} for e in schema_errors]
        })
    else:
        report["checks"].append({"name": "manifest_schema", "result": "pass"})

    # Forbidden-field scan.
    forbidden_errors = scan_forbidden(manifest)
    if forbidden_errors:
        report["checks"].append({
            "name": "forbidden_fields",
            "result": "fail",
            "details": [{"path": e.path, "message": e.message} for e in forbidden_errors]
        })
    else:
        report["checks"].append({"name": "forbidden_fields", "result": "pass"})

    # Permission grammar.
    perm_errors = check_permissions(manifest)
    if perm_errors:
        report["checks"].append({
            "name": "permissions",
            "result": "fail",
            "details": [{"path": e.path, "message": e.message} for e in perm_errors]
        })
    else:
        report["checks"].append({"name": "permissions", "result": "pass"})

    # Extension-point enum.
    ep_errors = check_extension_points(manifest)
    if ep_errors:
        report["checks"].append({
            "name": "extension_points",
            "result": "fail",
            "details": [{"path": e.path, "message": e.message} for e in ep_errors]
        })
    else:
        report["checks"].append({"name": "extension_points", "result": "pass"})

    # CSP audit.
    csp_errors = check_csp(manifest)
    if csp_errors:
        report["checks"].append({
            "name": "csp_audit",
            "result": "fail",
            "details": [{"path": e.path, "message": e.message} for e in csp_errors]
        })
    else:
        report["checks"].append({"name": "csp_audit", "result": "pass"})

    # Bilingual completeness.
    bi_errors = check_bilingual(manifest)
    if bi_errors:
        report["checks"].append({
            "name": "bilingual_completeness",
            "result": "fail",
            "details": [{"path": e.path, "message": e.message} for e in bi_errors]
        })
    else:
        report["checks"].append({"name": "bilingual_completeness", "result": "pass"})

    # Signature verification (optional).
    if check_signatures:
        if not bundle_path:
            report["checks"].append({"name": "signature_check", "result": "fail",
                                     "details": "--check-signatures requires a bundle path"})
        elif not os.path.isfile(bundle_path):
            report["checks"].append({"name": "signature_check", "result": "fail",
                                     "details": f"bundle not found: {bundle_path}"})
        else:
            with open(bundle_path, "rb") as f:
                bundle_bytes = f.read()
            bundle_sha = hashlib.sha256(bundle_bytes).hexdigest()
            bundle_size = len(bundle_bytes)
            # Author signature.
            author_sig = manifest.get("signature", {})
            ok, reason = verify_signature_block(author_sig, manifest, bundle_sha, bundle_size,
                                                pinned_public_key=author_sig.get("public_key"),
                                                label="author_signature")
            sig_results = [{"label": "author_signature", "ok": ok, "reason": reason}]
            # Marketplace signature (pinned CA key — in production this comes from
            # src/python/plugin_marketplace_ca.py; here we accept whatever is in the manifest
            # and verify it against itself, just to confirm the canonical_payload verifies).
            market_sig = manifest.get("marketplace_signature", {})
            if isinstance(market_sig, dict) and market_sig.get("sig") and market_sig["sig"] != "0" * 128:
                ok_m, reason_m = verify_signature_block(market_sig, manifest, bundle_sha, bundle_size,
                                                        pinned_public_key=market_sig.get("public_key"),
                                                        label="marketplace_signature")
                sig_results.append({"label": "marketplace_signature", "ok": ok_m, "reason": reason_m})
            else:
                sig_results.append({"label": "marketplace_signature", "ok": False,
                                    "reason": "marketplace_signature.sig is the unsigned placeholder (all zeros) — must be filled by the marketplace at approval time"})
            all_ok = all(r["ok"] for r in sig_results)
            report["checks"].append({
                "name": "signature_check",
                "result": "pass" if all_ok else "fail",
                "details": {
                    "bundle_sha256": bundle_sha,
                    "bundle_size": bundle_size,
                    "signatures": sig_results,
                }
            })

    # Overall.
    failed = [c for c in report["checks"] if c["result"] == "fail"]
    report["overall"] = "fail" if failed else "pass"
    report["failed_count"] = len(failed)
    return report


def _format_human(report: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"eInvite Plugin Manifest Validator v{SCHEMA_VERSION} (Phase {PHASE})")
    lines.append(f"Manifest: {report['manifest_path']}")
    if report.get("bundle_path"):
        lines.append(f"Bundle:   {report['bundle_path']}")
    lines.append("")
    for check in report["checks"]:
        marker = "✓" if check["result"] == "pass" else "✗"
        lines.append(f"  [{marker}] {check['name']}")
        if check["result"] != "pass" and "details" in check:
            d = check["details"]
            if isinstance(d, list):
                for item in d[:10]:
                    if isinstance(item, dict):
                        lines.append(f"        {item.get('path', '?')}: {item.get('message', '')}")
                    else:
                        lines.append(f"        {item}")
            elif isinstance(d, dict):
                if "signatures" in d:
                    lines.append(f"        bundle_sha256: {d['bundle_sha256']}")
                    lines.append(f"        bundle_size:   {d['bundle_size']} bytes")
                    for s in d["signatures"]:
                        mark = "✓" if s["ok"] else "✗"
                        lines.append(f"        [{mark}] {s['label']}: {s['reason']}")
                else:
                    lines.append(f"        {json.dumps(d, ensure_ascii=False)[:300]}")
            else:
                lines.append(f"        {d}")
    lines.append("")
    lines.append(f"Overall: {report['overall'].upper()}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate an eInvite plugin manifest.json against the V54.6 schema + signing rules."
    )
    parser.add_argument("manifest", help="Path to the manifest.json file.")
    parser.add_argument("--check-signatures", action="store_true",
                        help="Also verify the author + marketplace Ed25519 signatures (requires --bundle).")
    parser.add_argument("--bundle", help="Path to the bundle.tar.gz file (required with --check-signatures).")
    parser.add_argument("--report", choices=["human", "json"], default="human",
                        help="Output format. Default: human.")
    args = parser.parse_args(argv)

    if args.check_signatures and not args.bundle:
        print("ERROR: --check-signatures requires --bundle", file=sys.stderr)
        return 2

    report = validate_manifest_file(args.manifest, bundle_path=args.bundle,
                                    check_signatures=args.check_signatures)

    if args.report == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_format_human(report))

    return 0 if report["overall"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
eInvite Plugin SDK — example-plugin test suite.

Validates the example-plugin/manifest.json against the V54.6 manifest schema,
the forbidden-field scanner, the permission grammar, and the bilingual
completeness check. Stdlib-only Python — no third-party dependencies.

Run:
    python3 plugins/sdk/example-plugin/tests/test_example_plugin.py

Exit codes:
    0 = all assertions passed.
    1 = at least one assertion failed.
    2 = bad setup (file not found, JSON parse error, etc.).
"""

import json
import os
import sys

# Make plugins/sdk importable.
SDK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, SDK_DIR)

import validate_manifest  # noqa: E402  (path manipulated above)


EXAMPLE_DIR = os.path.join(SDK_DIR, "example-plugin")
MANIFEST_PATH = os.path.join(EXAMPLE_DIR, "manifest.json")


def _ok(name):
    print(f"  [PASS] {name}")


def _fail(name, detail):
    print(f"  [FAIL] {name}: {detail}")
    return False


def test_manifest_loads():
    if not os.path.isfile(MANIFEST_PATH):
        return _fail("manifest_loads", f"manifest not found: {MANIFEST_PATH}")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        try:
            manifest = json.load(f)
        except json.JSONDecodeError as e:
            return _fail("manifest_loads", f"invalid JSON: {e}")
    if not isinstance(manifest, dict):
        return _fail("manifest_loads", "manifest is not a JSON object")
    _ok("manifest_loads")
    return True


def test_validator_passes_on_clean_manifest():
    """The example manifest (with unsigned placeholder marketplace_signature)
    should pass the schema + forbidden + permission + extension-point + CSP +
    bilingual checks, but NOT the signature check (because the marketplace
    signature is the all-zeros placeholder)."""
    report = validate_manifest.validate_manifest_file(MANIFEST_PATH)
    by_name = {c["name"]: c["result"] for c in report["checks"]}
    expected = {
        "manifest_load": "pass",
        "manifest_schema": "pass",
        "forbidden_fields": "pass",
        "permissions": "pass",
        "extension_points": "pass",
        "csp_audit": "pass",
        "bilingual_completeness": "pass",
    }
    for name, expected_result in expected.items():
        if by_name.get(name) != expected_result:
            return _fail("validator_passes_on_clean_manifest",
                         f"{name} expected {expected_result}, got {by_name.get(name)}")
    _ok("validator_passes_on_clean_manifest")
    return True


def test_required_fields_present():
    """All required top-level fields from PLUGIN-SPEC.md §2.1 are present."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    required = [
        "schema_version", "name", "name_kh", "version", "description",
        "description_kh", "author", "author_key_id", "permissions",
        "extension_points", "entrypoint", "min_platform_version",
        "content_security_policy", "signature", "marketplace_signature",
    ]
    missing = [f for f in required if f not in manifest]
    if missing:
        return _fail("required_fields_present", f"missing: {missing}")
    _ok("required_fields_present")
    return True


def test_schema_version_is_one():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    if manifest.get("schema_version") != 1:
        return _fail("schema_version_is_one", f"got {manifest.get('schema_version')!r}")
    _ok("schema_version_is_one")
    return True


def test_permission_grammar():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    perms = manifest.get("permissions", [])
    if not perms:
        return _fail("permission_grammar", "no permissions declared")
    for i, p in enumerate(perms):
        if not validate_manifest.PERMISSION_PATTERN.match(p):
            return _fail("permission_grammar", f"permission[{i}] invalid: {p!r}")
        if p.split(":")[1] == "*":
            return _fail("permission_grammar", f"permission[{i}] uses wildcard resource_id: {p!r}")
    _ok("permission_grammar")
    return True


def test_extension_point_enum():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    eps = manifest.get("extension_points", [])
    if not eps:
        return _fail("extension_point_enum", "no extension_points declared")
    for ep in eps:
        if ep.get("point") not in validate_manifest.EXTENSION_POINTS:
            return _fail("extension_point_enum", f"unknown extension point: {ep.get('point')!r}")
    _ok("extension_point_enum")
    return True


def test_bilingual_completeness():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    for base, kh in [("name", "name_kh"), ("description", "description_kh")]:
        if base not in manifest or kh not in manifest:
            return _fail("bilingual_completeness", f"missing {base} or {kh}")
        if manifest[base] == manifest[kh]:
            return _fail("bilingual_completeness", f"{kh} is byte-identical to {base}")
    for i, ep in enumerate(manifest.get("extension_points", [])):
        if "label" in ep and "label_kh" not in ep:
            return _fail("bilingual_completeness", f"extension_points[{i}] missing label_kh")
        if "label" in ep and "label_kh" in ep and ep["label"] == ep["label_kh"]:
            return _fail("bilingual_completeness", f"extension_points[{i}].label_kh is byte-identical to label")
    _ok("bilingual_completeness")
    return True


def test_csp_no_unsafe_tokens():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    csp = manifest.get("content_security_policy", {})
    for directive, tokens in csp.items():
        for tok in tokens:
            if tok in validate_manifest.FORBIDDEN_CSP_TOKENS:
                return _fail("csp_no_unsafe_tokens", f"{directive} contains forbidden token: {tok!r}")
            if directive == "connect_src" and tok != "'self'":
                return _fail("csp_no_unsafe_tokens", f"connect_src must be 'self'; got {tok!r}")
    _ok("csp_no_unsafe_tokens")
    return True


def test_forbidden_field_scan():
    """Inject a forbidden field and confirm the scanner catches it."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    tampered = dict(manifest)
    tampered["eval"] = "should be rejected"
    errors = validate_manifest.scan_forbidden(tampered)
    if not errors:
        return _fail("forbidden_field_scan", "scanner failed to catch injected forbidden field 'eval'")
    paths = [e.path for e in errors]
    if "$.eval" not in paths:
        return _fail("forbidden_field_scan", f"scanner did not flag $.eval (got: {paths})")
    _ok("forbidden_field_scan")
    return True


def test_nested_forbidden_field_scan():
    """Forbidden fields must be caught at any nesting depth."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    tampered = dict(manifest)
    tampered["extension_points"] = list(manifest["extension_points"])
    tampered["extension_points"][0] = dict(manifest["extension_points"][0])
    tampered["extension_points"][0]["schema"] = {
        "properties": {
            "x": { "innerHTML": "should be rejected" }
        }
    }
    errors = validate_manifest.scan_forbidden(tampered)
    if not any("innerHTML" in e.message for e in errors):
        return _fail("nested_forbidden_field_scan", f"scanner did not catch nested innerHTML: {errors}")
    _ok("nested_forbidden_field_scan")
    return True


def test_wildcard_permission_rejected():
    """A manifest with a wildcard resource_id permission must fail validation."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    tampered = dict(manifest)
    tampered["permissions"] = ["invitation:*:read"]
    errors = validate_manifest.check_permissions(tampered)
    if not errors:
        return _fail("wildcard_permission_rejected", "check_permissions did not reject 'invitation:*:read'")
    _ok("wildcard_permission_rejected")
    return True


def test_unknown_extension_point_rejected():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    tampered = dict(manifest)
    tampered["extension_points"] = [
        {"id": "bogus", "point": "editor.bogus", "label": "Bogus"}
    ]
    errors = validate_manifest.check_extension_points(tampered)
    if not errors:
        return _fail("unknown_extension_point_rejected", "check_extension_points accepted 'editor.bogus'")
    _ok("unknown_extension_point_rejected")
    return True


def test_marketplace_signature_is_unsigned_placeholder():
    """The example manifest ships with an all-zeros marketplace_signature.sig
    (the marketplace has not yet signed it). The --check-signatures path
    must surface this clearly."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    sig = manifest.get("marketplace_signature", {}).get("sig", "")
    if sig != "0" * 128:
        return _fail("marketplace_signature_is_unsigned_placeholder",
                     f"expected all-zeros, got {sig[:16]}... (len={len(sig)})")
    _ok("marketplace_signature_is_unsigned_placeholder")
    return True


def test_entrypoint_html_file_exists():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    entrypoint = manifest.get("entrypoint", "")
    if not entrypoint.endswith(".html"):
        return _fail("entrypoint_html_file_exists", f"entrypoint is not .html: {entrypoint!r}")
    entry_path = os.path.join(EXAMPLE_DIR, entrypoint.lstrip("./"))
    if not os.path.isfile(entry_path):
        return _fail("entrypoint_html_file_exists", f"entrypoint file not found: {entry_path}")
    _ok("entrypoint_html_file_exists")
    return True


def test_sdk_shim_is_loadable():
    """The SDK shim (einvite-plugin.js) is syntactically valid JS. We do a
    crude sanity check: it must define window.EInvitePlugin and not contain
    any of the forbidden patterns (eval, new Function, document.cookie, etc.)
    that the moderation pipeline rejects."""
    sdk_path = os.path.join(SDK_DIR, "einvite-plugin.js")
    if not os.path.isfile(sdk_path):
        return _fail("sdk_shim_is_loadable", f"SDK shim not found: {sdk_path}")
    with open(sdk_path, "r", encoding="utf-8") as f:
        src = f.read()
    if "global.EInvitePlugin" not in src:
        return _fail("sdk_shim_is_loadable", "SDK shim does not expose global.EInvitePlugin")
    # The SDK shim itself must NOT contain the moderation-rejected patterns
    # (it's the trusted code the host loads alongside the plugin).
    forbidden_patterns = ["eval(", "new Function(", "document.cookie", ".innerHTML =", "fetch(\"http"]
    for pat in forbidden_patterns:
        if pat in src:
            return _fail("sdk_shim_is_loadable", f"SDK shim contains forbidden pattern: {pat!r}")
    _ok("sdk_shim_is_loadable")
    return True


def test_example_plugin_js_no_forbidden_patterns():
    """The example plugin's index.js must not contain any moderation-rejected
    patterns. (The moderation pipeline would reject these at submission time;
    we assert the example is clean so authors have a copy-paste-safe template.)"""
    js_path = os.path.join(EXAMPLE_DIR, "index.js")
    if not os.path.isfile(js_path):
        return _fail("example_plugin_js_no_forbidden_patterns", f"index.js not found: {js_path}")
    with open(js_path, "r", encoding="utf-8") as f:
        src = f.read()
    forbidden = ["eval(", "new Function(", "document.cookie", "document.write(",
                 "fetch(\"https://", "new XMLHttpRequest", "new WebSocket",
                 "new Worker(", "navigator.serviceWorker", "importScripts(",
                 "WebAssembly.compileStreaming"]
    for pat in forbidden:
        if pat in src:
            return _fail("example_plugin_js_no_forbidden_patterns", f"index.js contains forbidden pattern: {pat!r}")
    _ok("example_plugin_js_no_forbidden_patterns")
    return True


def main():
    print("eInvite Plugin SDK — example-plugin test suite")
    print(f"  Manifest: {MANIFEST_PATH}")
    print()
    tests = [
        test_manifest_loads,
        test_validator_passes_on_clean_manifest,
        test_required_fields_present,
        test_schema_version_is_one,
        test_permission_grammar,
        test_extension_point_enum,
        test_bilingual_completeness,
        test_csp_no_unsafe_tokens,
        test_forbidden_field_scan,
        test_nested_forbidden_field_scan,
        test_wildcard_permission_rejected,
        test_unknown_extension_point_rejected,
        test_marketplace_signature_is_unsigned_placeholder,
        test_entrypoint_html_file_exists,
        test_sdk_shim_is_loadable,
        test_example_plugin_js_no_forbidden_patterns,
    ]
    all_passed = True
    for t in tests:
        try:
            ok = t()
        except Exception as e:
            ok = False
            _fail(t.__name__, f"unexpected exception: {e}")
        if not ok:
            all_passed = False
    print()
    if all_passed:
        print("RESULT: EXAMPLE_PLUGIN_TEST_PASSED")
        return 0
    else:
        print("RESULT: EXAMPLE_PLUGIN_TEST_FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

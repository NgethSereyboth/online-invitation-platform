#!/usr/bin/env python3
"""CycloneDX 1.5 SBOM generator (Python stdlib only).

Reads ``docs/requirements-production.txt``, resolves each pinned dependency
against the PyPI JSON API (when the network is available), and emits a
CycloneDX 1.5 SBOM document to stdout.

Usage::

    python3 scripts/generate-sbom.py > sbom.cdx.json

Design notes
------------
* **Stdlib-only** — no ``cyclonedx-python-lib`` / ``pip-requirements-parser``
  dependency. The script must run in the sandbox Python without ``pip install``.
  This is the same constraint as ``scripts/check-bilingual-consistency.py``.
* **Network-optional** — if PyPI is unreachable (e.g. sandbox without network),
  the script still emits a valid SBOM but with ``hashes: []`` and a
  ``properties`` marker recording the gap. CI then re-runs the script with
  network access to fill in checksums at release time.
* **CycloneDX 1.5** — ``bomFormat: "CycloneDX"``, ``specVersion: "1.5"``.
  Components use ``type: "library"`` + ``bom-ref: "pkg:pypi/{name}@{version}"``
  (purl-style).  Hashes are emitted as ``alg: "SHA-256"`` (uppercase, per spec)
  when checksums can be resolved from the PyPI JSON ``digests.sha256`` field.
* The script does NOT execute ``pip`` — it only reads the requirements file
  and queries PyPI over HTTPS. Safe to run in CI without privileged access.

See:
* https://cyclonedx.org/docs/1.5/json/
* https://pypi.org/pypi/{package}/json
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

PYPI_URL_TEMPLATE = "https://pypi.org/pypi/{package}/json"
PYPI_TIMEOUT_SECONDS = 8.0
PYPI_RETRIES = 2
PYPI_BACKOFF_SECONDS = 0.5

REQUIREMENTS_PATH_DEFAULT = "docs/requirements-production.txt"


def _log(message: str) -> None:
    """Print a progress message to stderr (keeps stdout clean for the SBOM)."""
    print(f"[generate-sbom] {message}", file=sys.stderr)


def parse_requirements(path: str) -> List[Tuple[str, Optional[str]]]:
    """Parse a pip-style requirements file.

    Returns a list of ``(package_name, version)`` tuples. ``version`` is the
    pinned version if the requirement uses ``==`` or ``===``; otherwise ``None``
    (any version specifier — caller resolves the latest from PyPI).

    Comments, blank lines, ``-r``/``-c`` includes, and environment markers are
    skipped. Inline comments after a requirement (``foo # bar``) are stripped.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"requirements file not found: {path}")

    packages: List[Tuple[str, Optional[str]]] = []
    # Split on operators pip understands for direct pinning.
    pin_re = re.compile(r"^([A-Za-z0-9_.\-]+)\s*===?\s*([A-Za-z0-9_.\-+]+)")
    name_re = re.compile(r"^([A-Za-z0-9_.\-]+)")

    with open(path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("-"):
                # -r other.txt / -c constraints.txt / -e . / --hash=...
                continue
            # Strip environment markers: "foo>=1 ; python_version<'3.10'"
            line = line.split(";", 1)[0].strip()
            # Strip trailing version specifiers but keep the name.
            # First try a direct pin (== or ===).
            pin_match = pin_re.match(line)
            if pin_match:
                packages.append((pin_match.group(1), pin_match.group(2)))
                continue
            # Otherwise just take the bare package name.
            name_match = name_re.match(line)
            if name_match:
                # Normalize: lowercase, runs of - or _ -> -.
                name = re.sub(r"[-_]+", "-", name_match.group(1).lower())
                packages.append((name, None))
    return packages


def normalize_name(name: str) -> str:
    """PEP 503 normalisation: lowercase + runs of - or _ -> -."""
    return re.sub(r"[-_]+", "-", name).lower()


def fetch_pypi_info(package: str) -> Optional[Dict]:
    """Fetch the PyPI JSON metadata for ``package``.

    Returns ``None`` on any network or HTTP error after retries are exhausted.
    """
    url = PYPI_URL_TEMPLATE.format(package=package)
    last_error: Optional[str] = None
    for attempt in range(1, PYPI_RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "einvite-platform-generate-sbom/1.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=PYPI_TIMEOUT_SECONDS) as resp:
                if resp.status != 200:
                    last_error = f"HTTP {resp.status}"
                    continue
                data = resp.read()
                return json.loads(data.decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            _log(f"  PyPI fetch attempt {attempt}/{PYPI_RETRIES} for {package} failed: {last_error}")
            if attempt < PYPI_RETRIES:
                time.sleep(PYPI_BACKOFF_SECONDS * attempt)
    _log(f"  WARNING: could not reach PyPI for {package} ({last_error}); emitting without checksums")
    return None


def build_component(name: str, version: str, pypi_info: Optional[Dict]) -> Dict:
    """Build a CycloneDX 1.5 component dict for a single dependency."""
    purl = f"pkg:pypi/{normalize_name(name)}@{version}"
    component: Dict = {
        "type": "library",
        "bom-ref": purl,
        "name": name,
        "version": version,
        "purl": purl,
        "properties": [],
    }
    if pypi_info is not None:
        info = pypi_info.get("info", {}) or {}
        releases = pypi_info.get("releases", {}) or {}
        release_files = releases.get(version, []) or []
        # Prefer the sdist SHA-256 if a wheel isn't available; fall back to any
        # artifact with a sha256 digest.
        chosen_digest: Optional[str] = None
        chosen_url: Optional[str] = None
        for artifact in release_files:
            digests = artifact.get("digests", {}) or {}
            sha256 = digests.get("sha256")
            if sha256:
                chosen_digest = sha256
                chosen_url = artifact.get("url")
                break
        if chosen_digest:
            component["hashes"] = [{"alg": "SHA-256", "content": chosen_digest}]
            if chosen_url:
                component["externalReferences"] = [
                    {
                        "type": "distribution",
                        "url": chosen_url,
                    }
                ]
        if info.get("summary"):
            component["description"] = info["summary"]
        if info.get("home_page") or info.get("project_url"):
            homepage = info.get("home_page") or info.get("project_url")
            ext_refs = component.setdefault("externalReferences", [])
            if homepage and not any(ref.get("url") == homepage for ref in ext_refs):
                ext_refs.append({"type": "website", "url": homepage})
        license_expr = _extract_license(info)
        if license_expr:
            component["licenses"] = [{"license": {"id": license_expr}}]
    else:
        component["properties"].append(
            {
                "name": "einvite:network",
                "value": "pypi-unreachable",
            }
        )
    return component


def _extract_license(info: Dict) -> Optional[str]:
    """Best-effort SPDX license id extraction from PyPI metadata.

    PyPI's ``info.license`` field is freeform, often "MIT", "Apache-2.0",
    "BSD", "MPL-2.0", etc. We only return it if it matches the SPDX id pattern
    so the CycloneDX validator doesn't reject the document.
    """
    license_value = (info.get("license") or "").strip()
    if not license_value:
        return None
    # SPDX id pattern: short, alphanumeric, hyphen, dot, +.
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.\-+]*", license_value) and len(license_value) <= 40:
        return license_value
    return None


def build_bom(components: List[Dict], requirements_path: str, had_network: bool) -> Dict:
    """Build the top-level CycloneDX 1.5 BOM dict."""
    # CycloneDX 1.5 wants an RFC-4122 v4 / v5 urn:uuid for bom-ref.
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tools": [
                {
                    "vendor": "eInvite",
                    "name": "generate-sbom.py",
                    "version": "1.0.0",
                }
            ],
            "component": {
                "type": "application",
                "bom-ref": "pkg:generic/einvite-platform",
                "name": "einvite-platform",
                "version": "v54",
            },
            "properties": [
                {
                    "name": "einvite:requirements-source",
                    "value": requirements_path,
                },
                {
                    "name": "einvite:pypi-resolved",
                    "value": "true" if had_network else "false",
                },
            ],
        },
        "components": components,
    }
    # CycloneDX 1.5 spec: a top-level ``dependencies`` block is optional but
    # recommended. We don't track inter-package dependency edges (pip-audit /
    # ``pip freeze`` would be needed for that), so we emit a single node
    # pointing at the application component to keep the document well-formed.
    bom["dependencies"] = [
        {
            "ref": "pkg:generic/einvite-platform",
            "dependsOn": [c["bom-ref"] for c in components],
        }
    ]
    return bom


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    requirements_path = REQUIREMENTS_PATH_DEFAULT
    # Allow override via positional arg or env var (CI may run from another cwd).
    if argv:
        requirements_path = argv[0]
    elif os.environ.get("EINVITE_REQUIREMENTS"):
        requirements_path = os.environ["EINVITE_REQUIREMENTS"]

    _log(f"Reading requirements from {requirements_path}")
    packages = parse_requirements(requirements_path)
    if not packages:
        _log("ERROR: no packages parsed from requirements file")
        return 2
    _log(f"Parsed {len(packages)} package entries")

    components: List[Dict] = []
    network_failures = 0
    for name, version in packages:
        pypi_info = fetch_pypi_info(name)
        if pypi_info is None:
            network_failures += 1
            if version is None:
                # Without PyPI we have no version — skip rather than emit an
                # invalid component. CI re-runs with network will catch it.
                _log(f"  SKIP {name} (no version pin and PyPI unreachable)")
                continue
            resolved_version = version
        else:
            info = pypi_info.get("info", {}) or {}
            # Prefer the explicit pin from the requirements file; otherwise
            # fall back to PyPI's reported "latest version".
            resolved_version = version or info.get("version") or "0.0.0"
        component = build_component(name, resolved_version, pypi_info)
        components.append(component)
        _log(f"  + {name} @ {resolved_version}")

    had_network = network_failures == 0
    if not had_network:
        _log(
            f"WARNING: {network_failures} PyPI lookup(s) failed; "
            f"emitting SBOM without checksums for those components"
        )

    bom = build_bom(components, requirements_path, had_network)
    json.dump(bom, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    _log(f"Emitted CycloneDX 1.5 SBOM with {len(components)} components")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
verify_admin_ip_allowlist.py

Standalone check for the ROADMAP 4.2a admin-IP-allowlist work.
Retained as the verification harness for §4.2a — evidence of the test procedure.

Run from the repo root:

    python scripts/verify_admin_ip_allowlist.py

What it does:
  1. Checks whether the files the implementation agent claimed to create
     actually exist, and reports their real size / line count.
  2. If the module exists, imports it directly by path (bypassing package
     structure) and prints its public API.
  3. If the test file exists, runs it and shows the output.
  4. Prints a single clear verdict.

Exit code 0  -> everything present and passing
Exit code 1  -> something missing or failing (details printed above)
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MODULE = REPO / "src" / "python" / "core" / "admin_ip_allowlist.py"
TESTFILE = REPO / "tests" / "security_admin_ip_allowlist_test.py"

# Files the agent claimed to have created or modified.
CLAIMED = [
    MODULE,
    TESTFILE,
    REPO / "src" / "python" / "core" / "preflight.py",
    REPO / "src" / "python" / "server.py",
]


def rule(title: str) -> None:
    print()
    print("=" * 68)
    print(title)
    print("=" * 68)


def check_existence() -> bool:
    rule("1. File existence")

    all_present = True
    for path in CLAIMED:
        rel = path.relative_to(REPO)
        if path.is_file():
            size = path.stat().st_size
            try:
                lines = sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
            except OSError:
                lines = -1
            print(f"  PRESENT  {rel}   ({size} bytes, {lines} lines)")
        else:
            print(f"  MISSING  {rel}")
            all_present = False

    print()
    if not all_present:
        print("  -> At least one claimed file does not exist.")
    return all_present


def inspect_module() -> None:
    rule("2. Module inspection")

    if not MODULE.is_file():
        print(f"  Skipped - {MODULE.relative_to(REPO)} not found.")
        return

    spec = importlib.util.spec_from_file_location("admin_ip_allowlist", MODULE)
    if spec is None or spec.loader is None:
        print("  Could not build an import spec for the module.")
        return

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - report anything
        print(f"  Import FAILED: {type(exc).__name__}: {exc}")
        return

    public = sorted(n for n in dir(module) if not n.startswith("_"))
    print("  Import OK.")
    print(f"  Public names: {', '.join(public) if public else '(none)'}")

    # Try to exercise it, without assuming the exact API.
    exercised = False
    for name in ("AdminIPAllowlist", "Allowlist", "IPAllowlist"):
        cls = getattr(module, name, None)
        if cls is None:
            continue
        print(f"\n  Found class `{name}`. Attempting a smoke test...")
        try:
            instance = cls("10.0.0.0/8")
        except TypeError:
            try:
                instance = cls()
                for attr in ("add", "add_network", "allow"):
                    fn = getattr(instance, attr, None)
                    if callable(fn):
                        fn("10.0.0.0/8")
                        break
            except Exception as exc:  # noqa: BLE001
                print(f"    Could not construct: {type(exc).__name__}: {exc}")
                continue
        except Exception as exc:  # noqa: BLE001
            print(f"    Could not construct: {type(exc).__name__}: {exc}")
            continue

        check = None
        for attr in ("is_allowed", "allows", "contains", "matches"):
            fn = getattr(instance, attr, None)
            if callable(fn):
                check = fn
                break

        if check is None:
            print("    Constructed, but no `is_allowed`-style method found.")
            continue

        cases = [
            ("10.1.2.3", True, "inside 10.0.0.0/8"),
            ("11.0.0.1", False, "outside 10.0.0.0/8"),
            ("10.255.255.255", True, "upper bound"),
            ("2001:db8::1", False, "IPv6, not in an IPv4 range"),
        ]
        for ip, expected, note in cases:
            try:
                got = bool(check(ip))
            except Exception as exc:  # noqa: BLE001
                print(f"    {ip:<18} -> raised {type(exc).__name__}: {exc}")
                continue
            mark = "ok " if got == expected else "BAD"
            print(f"    [{mark}] {ip:<18} -> {got!s:<5} (expected {expected})  {note}")

        exercised = True
        break

    if not exercised:
        print("\n  Could not auto-exercise the module. Inspect its source directly.")


def run_testfile() -> int:
    rule("3. Project test file")

    if not TESTFILE.is_file():
        print(f"  Skipped - {TESTFILE.relative_to(REPO)} not found.")
        return 1

    print(f"  Running: python {TESTFILE.relative_to(REPO)}\n")
    try:
        proc = subprocess.run(
            [sys.executable, str(TESTFILE)],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        print("  TIMEOUT after 300s.")
        return 1
    except OSError as exc:
        print(f"  Could not launch: {exc}")
        return 1

    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print("--- stderr ---")
        print(proc.stderr.rstrip())

    print(f"\n  Exit code: {proc.returncode}")
    return proc.returncode


def main() -> int:
    print(f"Repo root: {REPO}")

    files_ok = check_existence()
    inspect_module()
    test_rc = run_testfile()

    rule("VERDICT")

    if not files_ok:
        print("  The implementation is NOT present.")
        print("  The agent's report described files that do not exist on disk.")
        print("  Nothing to test until the code is written.")
        return 1

    if test_rc != 0:
        print("  Files exist, but the project test did not pass.")
        print("  Scroll up: either the test failed on logic, or it could not run.")
        return 1

    print("  Files present and project test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
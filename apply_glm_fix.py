#!/usr/bin/env python3
"""Apply GLM's corrected test files back into the repo.

Handles the Windows-backslash zip bug GLM hit, verifies syntax before
overwriting anything, backs up tests/, and rolls back automatically if
any applied file fails to parse.

Usage:
  python apply_glm_fix.py C:\\Users\\NgethSereyboth\\Downloads\\<name>.zip --dry-run
  python apply_glm_fix.py C:\\Users\\NgethSereyboth\\Downloads\\<name>.zip
"""
from __future__ import annotations
import argparse
import py_compile
import shutil
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def extract_normalized(zip_path: Path, dest: Path) -> list[Path]:
    """Extract, turning backslashes in entry names into real directories."""
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/").lstrip("/")
            if ":" in name:
                name = name.split(":", 1)[-1].lstrip("/")
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as out:
                shutil.copyfileobj(src, out)
            written.append(target)
    return written


def find_tests_dir(staging: Path) -> Path | None:
    for candidate in staging.rglob("tests"):
        if candidate.is_dir() and any(candidate.glob("*.py")):
            return candidate
    return None


def verify_syntax(files: list[Path]) -> list[tuple[Path, str]]:
    failures = []
    for f in files:
        if f.suffix != ".py":
            continue
        cfile = Path(str(f) + ".syntaxcheck")
        try:
            py_compile.compile(str(f), doraise=True, cfile=str(cfile))
        except py_compile.PyCompileError as exc:
            failures.append((f, str(exc)))
        finally:
            cfile.unlink(missing_ok=True)
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("zip", type=Path, help="Path to the zip GLM produced")
    ap.add_argument("--dry-run", action="store_true",
                    help="Extract and verify only; do not touch the repo")
    ap.add_argument("--staging", type=Path,
                    default=REPO_ROOT / ".glm-staging",
                    help="Where to extract (default: .glm-staging)")
    args = ap.parse_args()

    zip_path = args.zip.expanduser().resolve()
    if not zip_path.is_file():
        print(f"ERROR: zip not found: {zip_path}")
        return 1

    if args.staging.exists():
        shutil.rmtree(args.staging)

    print(f"Extracting {zip_path.name}")
    written = extract_normalized(zip_path, args.staging)
    print(f"  {len(written)} files extracted to {args.staging}")

    tests_dir = find_tests_dir(args.staging)
    if tests_dir is None:
        print("ERROR: no tests/ folder with .py files in the zip.")
        print("Staging contents:")
        for p in sorted(args.staging.rglob("*"))[:60]:
            if p.is_file():
                print(f"  {p.relative_to(args.staging)}")
        return 1
    print(f"  tests dir: {tests_dir.relative_to(args.staging)}")

    py_files = sorted(tests_dir.rglob("*.py"))
    print(f"  {len(py_files)} .py files")
    print("Verifying syntax...")
    failures = verify_syntax(py_files)
    if failures:
        print(f"  {len(failures)} SYNTAX FAILURES:")
        for f, err in failures:
            last = err.strip().splitlines()[-1] if err.strip() else "(unknown)"
            print(f"    {f.name}: {last}")
        print("\nRefusing to apply.")
        return 2
    print("  all parse cleanly")

    repo_tests = REPO_ROOT / "tests"
    if not repo_tests.is_dir():
        print(f"ERROR: repo tests/ not found at {repo_tests}")
        return 1

    changed, new, same = [], [], []
    for f in py_files:
        target = repo_tests / f.name
        if not target.exists():
            new.append(f.name)
        elif target.read_bytes() == f.read_bytes():
            same.append(f.name)
        else:
            changed.append(f.name)

    print(f"\nDiff vs {repo_tests}:")
    print(f"  {len(changed)} modified: {', '.join(changed[:10])}"
          + (" ..." if len(changed) > 10 else ""))
    print(f"  {len(new)} new:      {', '.join(new) if new else '(none)'}")
    print(f"  {len(same)} identical")

    if args.dry_run:
        print(f"\n--dry-run: no files copied. Staging left at {args.staging}")
        return 0

    backup = REPO_ROOT / "tests.bak"
    if backup.exists():
        shutil.rmtree(backup)
    print(f"\nBacking up tests/ -> tests.bak")
    shutil.copytree(repo_tests, backup)

    print("Applying...")
    for f in py_files:
        shutil.copy2(f, repo_tests / f.name)
    print(f"  {len(py_files)} files written")

    print("Re-verifying applied files...")
    failures = verify_syntax([repo_tests / f.name for f in py_files])
    if failures:
        print(f"  {len(failures)} failures after copy — ROLLING BACK")
        shutil.rmtree(repo_tests)
        shutil.copytree(backup, repo_tests)
        return 3
    print("  ok")

    print("\nNext:")
    print("  python tests\\v13_editor_model_test.py")
    print("  python src\\python\\run_review_checks.py --skip-browser "
          "--continue-on-failure --fast-workers 8")
    print("\nRollback if needed:")
    print("  rmdir /s /q tests && move tests.bak tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
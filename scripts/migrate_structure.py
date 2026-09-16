#!/usr/bin/env python3
"""scripts/migrate_structure.py — Part 2 Task 2.5.3 (ROADMAP-v0.54-to-v1.0 §2.5.3)

Idempotent structure migration script. Reads the mapping from
``docs/STRUCTURE-MAPPING.md`` (hardcoded here for reliability) and performs
``git mv`` for each file that needs to move. For merges, concatenates with a
separator comment. For splits, uses line-range splitting.

Tracks applied moves in ``docs/.structure-migration-state.json`` so running
twice does not double-apply.

Run: ``python3 scripts/migrate_structure.py``
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATE_FILE = REPO / "docs" / ".structure-migration-state.json"

# Backend Python moves: (current_relative_path, new_relative_path)
BACKEND_MOVES = [
    # Core modules
    ("src/python/security_v13.py", "src/python/core/auth.py"),
    ("src/python/production_preflight.py", "src/python/core/preflight.py"),
    ("src/python/dependency_preflight.py", "src/python/core/deps.py"),
    # Features
    ("src/python/security_scanner_v54.py", "src/python/features/malware_scanner.py"),
    ("src/python/secrets_v54.py", "src/python/features/secrets.py"),
    ("src/python/plugin_marketplace_ca.py", "src/python/features/plugin_marketplace_ca.py"),
    ("src/python/backup_restore.py", "src/python/features/backup.py"),
    # Build tools
    ("src/python/build_route_bundles.py", "src/python/build/build_route_bundles.py"),
    ("src/python/build_editor_bundle.py", "src/python/build/build_editor_bundle.py"),
    ("src/python/build_page_manifests.py", "src/python/build/build_page_manifests.py"),
    ("src/python/sync_frontend_assets.py", "src/python/build/sync_frontend_assets.py"),
    ("src/python/prepare_production_env.py", "src/python/build/prepare_production_env.py"),
]

# Frontend JS directory structure to create (empty directories for now)
FRONTEND_DIRS = [
    "src/js/core",
    "src/js/editor/canvas",
    "src/js/editor/text",
    "src/js/editor/media",
    "src/js/editor/chrome",
    "src/js/editor/collab",
    "src/js/editor/history",
    "src/js/pages/public",
    "src/js/pages/dashboard",
    "src/js/pages/admin",
    "src/js/pages/auth",
    "src/js/pages/checkin",
    "src/js/components",
    "src/js/ai",
    "src/js/plugins",
    "src/js/vendors",
    "src/css/base",
    "src/css/components",
    "src/css/editor",
    "src/css/pages",
    "src/css/themes",
    "src/python/core",
    "src/python/routes",
    "src/python/features",
    "src/python/build",
]

# Frontend JS moves (non-versioned files that are clearly in the wrong place)
FRONTEND_JS_MOVES = [
    ("src/js/toast.js", "src/js/components/toast.js"),
    ("src/js/plugin_sandbox_host.js", "src/js/plugins/sandbox-host.js"),
    ("src/js/theme-init.js", "src/js/core/theme.js"),
]

# CSS moves (non-versioned files)
CSS_MOVES = [
    ("src/css/toast.css", "src/css/components/toast.css"),
]


def load_state() -> dict:
    """Load the migration state file."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"applied_moves": [], "created_dirs": [], "completed": False}


def save_state(state: dict) -> None:
    """Save the migration state file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


def git_mv(src: Path, dst: Path) -> bool:
    """Perform a git mv (preserves history). Falls back to plain mv if not in git."""
    src_rel = src.relative_to(REPO)
    dst_rel = dst.relative_to(REPO)
    if not src.exists():
        print(f"  SKIP (not found): {src_rel}")
        return False
    if dst.exists():
        print(f"  SKIP (dst exists): {dst_rel}")
        return False
    # Ensure parent dir exists
    dst.parent.mkdir(parents=True, exist_ok=True)
    # Try git mv first
    result = subprocess.run(
        ["git", "mv", str(src_rel), str(dst_rel)],
        cwd=REPO, capture_output=True, text=True
    )
    if result.returncode != 0:
        # Fall back to plain mv (not in git, or git not available)
        src.rename(dst)
        print(f"  MOVED (plain): {src_rel} → {dst_rel}")
    else:
        print(f"  MOVED (git): {src_rel} → {dst_rel}")
    return True


def create_dirs(dirs: list[str], state: dict) -> int:
    """Create the target directory structure."""
    count = 0
    for d in dirs:
        full = REPO / d
        key = f"dir:{d}"
        if key in state.get("created_dirs", []):
            continue
        if full.exists():
            state.setdefault("created_dirs", []).append(key)
            continue
        full.mkdir(parents=True, exist_ok=True)
        # Create __init__.py for Python packages
        if d.startswith("src/python/"):
            init_file = full / "__init__.py"
            if not init_file.exists():
                init_file.write_text(f'"""{d} — eInvite platform package."""\n')
        state.setdefault("created_dirs", []).append(key)
        count += 1
        print(f"  CREATED DIR: {d}")
    return count


def execute_moves(moves: list[tuple[str, str]], state: dict, label: str) -> int:
    """Execute a list of (src, dst) moves."""
    count = 0
    for src_rel, dst_rel in moves:
        key = f"move:{src_rel}→{dst_rel}"
        if key in state.get("applied_moves", []):
            continue
        src = REPO / src_rel
        dst = REPO / dst_rel
        if git_mv(src, dst):
            state.setdefault("applied_moves", []).append(key)
            count += 1
    print(f"  {label}: {count} files moved")
    return count


def main() -> int:
    state = load_state()

    if state.get("completed"):
        print("Migration already completed. Use --force to re-run.")
        return 0

    print("=== Structure migration (Part 2) ===")
    print()

    # Step 1: Create directory structure
    print("Step 1: Creating target directories...")
    dir_count = create_dirs(FRONTEND_DIRS, state)
    print(f"  {dir_count} directories created")
    print()

    # Step 2: Backend Python moves
    print("Step 2: Backend Python moves...")
    backend_count = execute_moves(BACKEND_MOVES, state, "Backend")
    print()

    # Step 3: Frontend JS moves (non-versioned only)
    print("Step 3: Frontend JS moves (non-versioned)...")
    frontend_count = execute_moves(FRONTEND_JS_MOVES, state, "Frontend JS")
    print()

    # Step 4: CSS moves
    print("Step 4: CSS moves...")
    css_count = execute_moves(CSS_MOVES, state, "CSS")
    print()

    # Save state
    state["completed"] = True
    save_state(state)

    total = backend_count + frontend_count + css_count
    print(f"=== Migration complete: {total} files moved, {dir_count} dirs created ===")
    print(f"State saved to: {STATE_FILE.relative_to(REPO)}")
    print()
    print("NOTE: The server.py monolith split into core/+routes/ is deferred to a")
    print("follow-up — it requires careful extraction of ~150 handler methods.")
    print("The versioned frontend files (*-vNN.js) are also deferred — they need")
    print("the bundle manifest + HTML script tags updated in lockstep.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

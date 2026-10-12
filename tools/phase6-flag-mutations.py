"""phase6-flag-mutations.py — do the assertions test_phase6_live_endpoint_feature_flag
adds actually bite?

Why this exists
---------------
The flag test's 200-branch used to be unreachable: it POSTed to a PUT-only, admin-only
route, took its own `else` branch, printed "skipped" and passed. Fixing the fixture
(tests/analytics_reports_test.py: promote the host to admin, PUT the documented
`{"updates": [...]}` body — see tools/evidence/instrument-repair-flag-branch.txt) makes
the branch run, but a test that passes is not yet evidence that it *would fail*. This
harness injects one mutation per assertion seam, at the seams the test itself uses, and
requires every mutation to make the test fail. A surviving mutation means the branch is
running without being asserted, which is how the defect got in.

    python3 tools/phase6-flag-mutations.py      # from the repo root; exit 0 = all killed

Three mutations, one per seam:
  1. the admin PUT returns 500                  -> the "PUT should flip the flag" assertion
  2. the PUT flips a different flag             -> the "1 flag updated" assertion
  3. the user is never promoted to admin        -> the 403-vs-200 assertion

Requires the repo's virtualenv (`.venv`) and the test module's own fixtures; it calls the
test function directly rather than through pytest, so it needs no server of its own.
Exit status: 0 when every mutation is killed, 1 otherwise.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "python"))

import tests.analytics_reports_test as T  # noqa: E402


def run(label, patch) -> bool:
    """Apply a mutation, run the test, restore the seams. Returns True if it was killed."""
    orig_put, orig_promote = T._put, T._promote_to_admin
    patch()
    try:
        T.test_phase6_live_endpoint_feature_flag()
        print(f"[MUTATION SURVIVED] {label} — the test passed anyway")
        return False
    except AssertionError as e:
        print(f"[MUTATION KILLED]   {label} — {e}")
        return True
    finally:
        T._put, T._promote_to_admin = orig_put, orig_promote


def break_put():
    """The admin PUT does not happen: the flag-ON branch must not be reachable."""
    T._put = lambda base, path, body, headers=None: (500, b'{"error":"broken"}')


def wrong_flag():
    """The PUT succeeds but flips the WRONG flag: the live-200 assertion must bite."""
    orig = T._put
    T._put = lambda base, path, body, headers=None: orig(
        base, path, {"updates": [{"key": "ai_agent_enabled", "value": True}]}, headers
    )


def no_promote():
    """The user is never promoted: the admin route must refuse."""
    T._promote_to_admin = lambda data_dir, email: None


def main() -> int:
    results = [
        run("admin PUT returns 500", break_put),
        run("admin PUT flips ai_agent_enabled instead", wrong_flag),
        run("user never promoted to admin", no_promote),
    ]
    killed = sum(1 for r in results if r)
    print(f"MUTATIONS {killed}/{len(results)} killed")
    return 0 if killed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

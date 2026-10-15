# Plan 002: Return 404 (not 401) to logged-in non-members of host-only invitation endpoints, and 401 before any lookup for anonymous callers

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving on. If anything in "STOP conditions" occurs, stop and report — do not improvise. When done, update the row for plan 002 in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 39c8ef1..HEAD -- src/python/server.py tests/security_tenant_isolation_test.py`
> If the function or test changed since this plan was written, compare the "Current state" excerpts with the live code; on a mismatch, STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW (touches only the failure branch of one access helper; success paths unchanged)
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `39c8ef1`, 2026-10-14

## Why this matters

`tests/security_tenant_isolation_test.py` runs 26 cross-tenant attacks. Bob (a logged-in user with no role on Alice's invitation) gets `401 {"error": "Authentication required"}` on `GET /api/invitations/{id}/edit-history` and `GET /api/invitations/{id}/deliveries`. The test expects 403 or 404 for a non-member, and it fails on those two requests. No data leaked in the run. The bigger issue is an existence oracle: for a logged-in user, a nonexistent invitation returns `404 Invitation not found`, but an existing invitation the user cannot access returns `401`. That tells any logged-in user which invitation IDs exist. The fix makes non-members indistinguishable from missing invitations.

## Current state

`src/python/server.py`, function `_p2a_resolve_access` (starts at line 8996). Relevant control flow (lines 9008–9037, excerpt):

```python
user = self.user()
with connect() as db:
    invitation = db.execute(
        "SELECT id,slug,owner_id,access_mode,is_published,archived,deleted_at,access_password_hash FROM invitations WHERE id=?",
        (invite_id,)
    ).fetchone()
    if not invitation or invitation["deleted_at"]:
        self.json(404, {"error": "Invitation not found"}); return None
    if user:
        role = self.invitation_role(db, invite_id, user["id"])
        if role is not None:
            if require_manage and role not in {"owner", "manager"}:
                self.json(403, {"error": "Invitation management permission required"}); return None
            ...
            return {"mode": "host", ...}
    if not allow_guest:
        self.json(401, {"error": "Authentication required"}); return None
    if not invitation["is_published"] or invitation["archived"]:
        self.json(404, {"error": "Invitation not found"}); return None
```

Host-only callers pass `allow_guest=False`, for example `list_edit_history` (server.py line 9715) and `list_deliveries` (line 9878), both with `require_manage=True`. Find all callers with `grep -n "_p2a_resolve_access(" src/python/server.py`.

Consequences in the current code:
- Missing or deleted invitation → 404.
- Existing invitation, logged-in non-member → 401 (wrong status; oracle).
- Existing invitation, anonymous → 401 (also an oracle, because the lookup runs before the auth check, so the response differs from a missing invitation only by status code. Make it the same shape as well: see Step 2).
- Existing invitation, member with insufficient role → 403 (keep as is; the caller already knows the invitation exists).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Tenant isolation test | `python3 tests/security_tenant_isolation_test.py; echo $?` | last line `TENANT_ISOLATION_TEST_PASSED`, exit 0 |
| Find expectations of 401 on these routes | `grep -rn "Authentication required" tests/ \| head -40` | list, read each hit (see Step 1) |
| Boundary test | `python3 tests/v0_52_security_boundary_test.py; echo $?` | exit 0 (if it does not run in this environment, report it; do not skip silently) |
| Make gate | `make check; echo $?` | exit 0 |

## Scope

**In scope**:
- `src/python/server.py` — function `_p2a_resolve_access` only.
- `tests/security_tenant_isolation_test.py` — ONLY if a test asserts an outdated status for an access path this plan intentionally changes, and only to match the new documented contract (404 for non-members). Do not weaken any assertion (no removing checks, no broadening to "any non-200").

**Out of scope**:
- Guest-mode behavior (`allow_guest=True` endpoints). Their behavior must not change.
- The 403 responses for members with insufficient role.
- Any other route or helper.
- `src/js/**`.

## Steps

### Step 1: Find test expectations that depend on 401
Run `grep -rn "Authentication required\|401" tests/security_tenant_isolation_test.py tests/v0_52_security_boundary_test.py tests/security_*_test.py`. For each hit that concerns invitation endpoints, read the assertion. Record in your report which tests assert 401 for an invitation route with an existing invitation. If any test asserts 401 for an anonymous request on an existing invitation and you cannot reconcile it with Step 2, STOP and report (see STOP conditions).

**Verify**: the grep runs; you have a written list (may be empty) of affected assertions.

### Step 2: Change the failure branch
Edit `_p2a_resolve_access` so that, for `allow_guest=False`:

1. Anonymous callers (`user is None`) get `401 Authentication required` BEFORE the invitation lookup, so the response does not depend on whether the invitation exists.
2. Logged-in callers who are not members get `404 {"error": "Invitation not found"}` — the same body as a missing invitation — instead of 401. Put this check in the same place as the existing `if user:` block, after the role check: when `role is None` and `not allow_guest`, return the 404.

Target shape (the guest path below it is unchanged):

```python
user = self.user()
if user is None and not allow_guest:
    self.json(401, {"error": "Authentication required"}); return None
with connect() as db:
    invitation = db.execute(...same SELECT...).fetchone()
    if not invitation or invitation["deleted_at"]:
        self.json(404, {"error": "Invitation not found"}); return None
    if user:
        role = self.invitation_role(db, invite_id, user["id"])
        if role is not None:
            ...unchanged 403s and host return...
    if not allow_guest:
        self.json(404, {"error": "Invitation not found"}); return None   # replaces the old 401 line
    if not invitation["is_published"] or invitation["archived"]:
        self.json(404, {"error": "Invitation not found"}); return None
    ...guest path unchanged...
```

Behavior that must hold: anonymous → 401 before any lookup; logged-in non-member → 404 with the same body as a missing invitation; member with insufficient role → 403 (unchanged); `allow_guest=True` paths → unchanged.

Do not change the messages of the existing 403s.

**Verify**: `python3 -m py_compile src/python/server.py; echo $?` → `0`. `grep -n "Authentication required" src/python/server.py` → the 401 is now before the `with connect()` block inside `_p2a_resolve_access`.

### Step 3: Run the tenant isolation test
**Verify**: `python3 tests/security_tenant_isolation_test.py; echo $?` → exit `0`, output shows `Failures: 0` and `TENANT_ISOLATION_TEST_PASSED`. Before this change it showed `Failures: 2`.

### Step 4: Run related tests
**Verify**: run `python3 tests/v0_52_security_boundary_test.py; echo $?` → exit `0`. If the script cannot run in this environment (missing dependency or service), record the exact error and report it as a limitation. Do not mark it passed.

### Step 5: Make gate
**Verify**: `make check; echo $?` → `0`.

## Test plan

- The existing `tests/security_tenant_isolation_test.py` is the acceptance test. It already covers Bob → Alice's edit-history and deliveries.
- Add (only if no equivalent exists) a case to the same test file asserting that an anonymous request to `/api/invitations/<existing-id>/edit-history` returns 401 and a missing ID returns 404. Model it on the existing attack list in that file. Do not delete or weaken existing cases.
- Verification: `python3 tests/security_tenant_isolation_test.py; echo $?` → exit 0, `Failures: 0`.

## Done criteria

- [ ] `python3 tests/security_tenant_isolation_test.py; echo $?` → `0` with `Failures: 0`
- [ ] `grep -n "Invitation not found" src/python/server.py` shows the logged-in non-member path returning this body for `allow_guest=False`
- [ ] `python3 -m py_compile src/python/server.py; echo $?` → `0`
- [ ] `make check; echo $?` → `0`
- [ ] `git status --short` lists only `src/python/server.py` and (if changed) `tests/security_tenant_isolation_test.py`
- [ ] `plans/README.md` row for 002 updated

## STOP conditions

- Step 1 finds a test asserting 401 for an existing invitation that is incompatible with the new contract, and you cannot justify updating it. Report it.
- Any guest-mode (`allow_guest=True`) test starts failing. That means the change leaked outside the intended branch; revert your edit and STOP.
- `security_tenant_isolation_test.py` still shows failures after the change. Do not edit the test's expectations to make it pass. Report the new response bodies.

## Maintenance notes

- Reviewers: confirm that no path returns a different body for "exists but not yours" than for "does not exist" (for logged-in and anonymous callers).
- The guest path (`allow_guest=True`) still returns 404 for unpublished or archived invitations; that is unchanged and intentional.
- Every route that calls `_p2a_resolve_access` with `allow_guest=False` inherits this change. That is intended.

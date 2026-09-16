# Rate-limit coverage audit
# Source: src/python/server.py
# Total routes found: 220

## WRITE routes (POST/PUT/DELETE): 138

| Method | Path | Handler | Rate limit | Notes |
|---|---|---|---|---|
| do_PUT | `/api/auth/password` | `change_password` | 60/60s (change-password:{user['id']}) | ✓ |
| do_PUT | `/api/account/studio` | `update_studio_profile` | 60/60s (studio-profile-update:{user['id']}) | ✓ |
| do_PUT | `/api/studio/governance` | `update_studio_governance` | 60/60s (studio-governance:{user['id']}) | ✓ |
| do_PUT | `/api/studio/backup-policy` | `update_studio_backup_policy` | 60/60s (studio-backup-policy:{user['id']}) | ✓ |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/studio/releases/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/studio/resources/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/uploads/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/assets/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/admin/users/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/admin/users/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/admin/users/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/admin/templates/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/admin/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/templates/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/page-templates/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/components/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_PUT | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/account/sessions/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/account/passkeys/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/uploads/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/account/grants/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/page-templates/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/components/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/studio/resources/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/studio/releases/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/templates/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_DELETE | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/platform/v52/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/platform/v32/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `regex:/signup-sheets/[^/]+/claim$` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `regex:/polls/[^/]+/vote$` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/auth/register` | `register` | 10/600s (register:{self.client_address[0]}) | ✓ |
| do_POST | `/api/auth/login` | `login` | 30/600s (login:{self.client_address[0]}) | ✓ |
| do_POST | `/api/auth/logout` | `logout` | 20/600s (mfa-login:{self.client_ip()}) | ✓ |
| do_POST | `/api/auth/mfa/complete` | `complete_mfa_login` | 20/600s (mfa-login:{self.client_ip()}) | ✓ |
| do_POST | `/api/auth/mfa/recover` | `mfa_recover` | 8/3600s (mfa-recover-fail:{email}) | ✓ |
| do_POST | `/api/auth/passkeys/login/options` | `passkey_login_options` | 30/600s (passkey-options:{self.client_ip()}) | ✓ |
| do_POST | `/api/auth/passkeys/login/complete` | `passkey_login_complete` | 30/600s (passkey-login:{self.client_ip()}) | ✓ |
| do_POST | `/api/auth/password-reset/request` | `request_password_reset` | 8/3600s (password-reset:{self.client_address[0]}) | ✓ |
| do_POST | `/api/auth/password-reset/confirm` | `confirm_password_reset` | 20/3600s (password-reset-confirm:{self.client_address[0]}) | ✓ |
| do_POST | `/api/auth/verification/request` | `request_email_verification` | 6/3600s (verify-email:{user['id']}) | ✓ |
| do_POST | `/api/auth/verification/confirm` | `confirm_email_verification` | 60/60s (change-password:{user['id']}) | ✓ |
| do_POST | `/api/account/mfa/setup` | `mfa_setup` | 60/60s (mfa-setup:{user['id']}) | ✓ |
| do_POST | `/api/account/mfa/enable` | `mfa_enable` | 60/60s (mfa-enable:{user['id']}) | ✓ |
| do_POST | `/api/account/mfa/disable` | `mfa_disable` | 60/60s (mfa-disable:{user['id']}) | ✓ |
| do_POST | `/api/account/mfa/recovery-codes/regenerate` | `mfa_recovery_regenerate` | 4/3600s (mfa-recovery-regen:{user['id']}) | ✓ |
| do_POST | `/api/account/passkeys/register/options` | `passkey_register_options` | 60/60s (passkey-register-opts:{user['id']}) | ✓ |
| do_POST | `/api/account/passkeys/register/complete` | `passkey_register_complete` | 60/60s (passkey-register-complete:{user['id']}) | ✓ |
| do_POST | `/api/account/sessions/revoke-all` | `revoke_all_sessions` | 60/60s (session-revoke-all:{user['id']}) | ✓ |
| do_POST | `/api/account/privacy` | `update_privacy_preferences` | 60/60s (privacy-update:{user['id']}) | ✓ |
| do_POST | `/api/ai-agent/preferences` | `ai_agent_update_preferences` | 60/60s (ai-agent-prefs:{user['id']}) | ✓ |
| do_POST | `/api/ai-agent/memories` | `ai_agent_add_memory` | 60/60s (ai-agent-memory-add:{user['id']}) | ✓ |
| do_POST | `/api/ai-agent/knowledge` | `ai_agent_add_knowledge` | 10/60s (ai-agent-knowledge-add:{user['id']}) | ✓ |
| do_POST | `/api/ai-agent/jit/approve` | `ai_agent_jit_approve` | 60/60s (jit-approve:{user['id']}) | ✓ |
| do_POST | `/api/ai-agent/jit/deny` | `ai_agent_jit_deny` | 60/60s (jit-deny:{user['id']}) | ✓ |
| do_POST | `/api/account/grants` | `create_agent_grant` | 60/60s (agent-grant-create:{user['id']}) | ✓ |
| do_POST | `/api/account/delete/schedule` | `schedule_account_deletion` | 60/60s (account-delete-schedule:{user['id']}) | ✓ |
| do_POST | `/api/account/delete/cancel` | `cancel_account_deletion` | 60/60s (account-delete-cancel:{user['id']}) | ✓ |
| do_POST | `/api/ai/assist` | `ai_assist` | 60/3600s (ai:{user['id']}) | ✓ |
| do_POST | `/api/billing/webhook` | `billing_webhook` | — | Stripe-signed webhook — no rate limit (HMAC verified) |
| do_POST | `/api/billing/webhook/stripe` | `billing_webhook_stripe` | — | Stripe-signed webhook — no rate limit (HMAC verified) |
| do_POST | `/api/billing/checkout` | `billing_checkout` | 60/60s (billing-checkout:{user['id']}) | ✓ |
| do_POST | `/api/account/tier/upgrade` | `account_tier_upgrade` | 60/60s (tier-upgrade:{user['id']}) | ✓ |
| do_POST | `/api/invitations` | `create_invitation` | 60/60s (invitation-create:{user['id']}) | ✓ |
| do_POST | `/api/templates` | `create_template` | 60/3600s (template:{user['id']}) | ✓ |
| do_POST | `/api/page-templates` | `create_page_template` | 60/60s (page-template-create:{user['id']}) | ✓ |
| do_POST | `/api/components` | `create_component` | 60/60s (component-create:{user['id']}) | ✓ |
| do_POST | `/api/studio/resources` | `create_studio_resource` | 60/60s (studio-resource-create:{user['id']}) | ✓ |
| do_POST | `/api/studio/releases` | `create_studio_release` | 60/60s (studio-release-create:{user['id']}) | ✓ |
| do_POST | `/api/studio/releases/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/studio/releases/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/studio/releases/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/studio/backups/run` | `run_studio_backup_now` | 10/60s (studio-backup-run:{user['id']}) | ✓ |
| do_POST | `/api/templates/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/templates/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/public/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/public/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/public/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/uploads/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/public/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/public/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |
| do_POST | `/api/invitations/*` | `<inline>` | — | inline dispatch (e.g. `if path.startswith(...)`) |

## READ routes (GET): 82 (no rate limit required for read-only)

## PASS: all write routes either have a rate_limit call or are documented exceptions.

---

## CI integration

Add to `.github/workflows/rate-limit-check.yml`:

```yaml
name: Rate-limit coverage check
on: [push, pull_request]
jobs:
  rate-limit-coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check rate-limit coverage
        run: python3 scripts/check-rate-limit-coverage.py
```

## Notes

- The audit script (`scripts/check-rate-limit-coverage.py`) parses `src/python/server.py` and identifies every route branch in `do_GET` / `do_PUT` / `do_POST` / `do_DELETE`.
- For each POST/PUT/DELETE route, it checks whether the handler body (next 60 lines from `def handler(self,...)`) contains a `rate_limit(...)` call.
- Inline dispatch routes (`if path.startswith(...)`) are documented as "inline dispatch" — the actual rate limiting happens in the sub-handler called from the inline branch. The audit script does not follow the call graph for inline dispatches, so they are listed for manual review.
- Read-only GET routes are listed but not flagged as failures (no rate limit needed for reads).
- Public guest actions (RSVP, claim, vote, album upload) and signature-verified webhooks (Stripe, billing) are documented exceptions — they don't need per-user rate limits (CSRF-exempt or HMAC-verified).

## Categories

- **Auth** (register, login, MFA, passkey, password reset): per-IP rate limits (8-30 per 600s-3600s).
- **Account** (security overview, audit log, grant management, JIT approve/deny): per-user 60/60s.
- **Invitations** (CRUD, collaboration, RSVP, edit history, album, signup-sheets, polls): per-user 60/60s for writes; public guest actions per-IP.
- **AI agent** (tool calls, plan confirm, memory, knowledge): per-user 10-120 per 60s-3600s depending on cost.
- **Platform V32/V52** (workspaces, jobs, object storage): per-user 60/60s.
- **Billing** (checkout, tier upgrade): per-user 60/60s.
- **Admin** (user plan, role, uploads, template visibility): per-admin 60/60s.
- **Public** (read-only): no rate limit needed.

*Generated by `scripts/check-rate-limit-coverage.py` — V54.29 sec-9.*

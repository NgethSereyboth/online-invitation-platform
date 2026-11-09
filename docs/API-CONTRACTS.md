# eInvite API Contracts

**Status:** enforced by `tests/api_contract_test.py` against a real local server.
**Scope:** the core authentication, invitation, guest, and check-in routes refactored by the
Sprint 3/4 work.

These contracts describe the current public JSON behavior. They do not replace the versioned
document validator: invitation `document` objects contain versioned extension keys, so the stable
core is pinned and those extensions are allowed to evolve.

## Conventions

- All responses in scope use `Content-Type: application/json; charset=utf-8`.
- Every response carries `X-Request-ID`. The value is generated or sanitized by the server and
  matches `^[A-Za-z0-9._:-]{1,80}$`.
- Bearer tokens are a development/test compatibility path (`EINVITE_DEV_AUTH_TOKENS=1`); production
  browser sessions use the HttpOnly cookie plus CSRF token.
- Unknown top-level response keys are rejected by the strict schemas unless a route is explicitly
  documented as carrying a versioned detail object.
- The test file implements the small JSON-Schema subset it needs locally, so the contract suite adds
  no runtime or test dependency.
- The server does not guarantee field ordering.

## Endpoint index

| # | Method | Path | Auth | Success | Expected errors |
|---:|---|---|---|---:|---|
| 1 | GET | `/api/health/live` | none | 200 | — |
| 2 | POST | `/api/auth/register` | none | 201 | 400, 409 |
| 3 | POST | `/api/auth/login` | none | 201 | 401, 423 |
| 4 | GET | `/api/auth/me` | optional | 200 | — |
| 5 | POST | `/api/auth/logout` | optional | 200 | — |
| 6 | GET | `/api/invitations` | session/token | 200 | 401, 400 |
| 7 | POST | `/api/invitations` | session/token | 201 | 400, 401 |
| 8 | GET | `/api/invitations/{id}` | read access | 200 | 401, 404 |
| 9 | PUT | `/api/invitations/{id}` | edit access | 200 | 400, 403, 404, 409 |
| 10 | POST | `/api/invitations/{id}/publish` | manage access | 201 | 401, 403, 404, 409 |
| 11 | DELETE | `/api/invitations/{id}` | owner | 200 | 401, 404 |
| 12 | POST | `/api/invitations/{id}/guests` | manage access | 201 | 400, 401, 403 |
| 13 | GET | `/api/invitations/{id}/guests` | manage access | 200 | 401, 403 |
| 14 | PUT | `/api/invitations/{id}/guests/{guestId}/check-in` | manage access | 200 | 401, 403, 404 |

The test file exercises the success schema for all 14 routes and the listed error families for the
mutation/read routes.

## 1. `GET /api/health/live`

**200**

| Field | Type | Required | Notes |
|---|---|---:|---|
| `ok` | boolean | yes | `true` |
| `status` | string | yes | `"live"` |

No version or infrastructure detail is returned.

## 2. `POST /api/auth/register`

Request: `{ "email": string, "password": string, "botToken"?: string }`.

**201 — session envelope**

| Field | Type | Required | Notes |
|---|---|---:|---|
| `user` | object | yes | Session user, below |
| `expiresAt` | integer | yes | Epoch milliseconds |
| `csrfToken` | string | yes | Cookie-session CSRF token |
| `token` | string | no | Present only when development bearer tokens are enabled |

**Session user**

| Field | Type | Required |
|---|---|---:|
| `id` | string | yes |
| `email` | string | yes |
| `role` | string | yes |
| `emailVerified` | boolean | yes |
| `plan` | string | yes |
| `uploadEnabled` | boolean | yes |
| `mfaEnabled` | boolean | yes |

**Errors:** `400` for invalid email/password or malformed JSON; `409` when the email already exists.
The error uses the standardized error schema below.

## 3. `POST /api/auth/login`

Request: `{ "email": string, "password": string }`.

**201 — same session envelope as registration.**
**Errors:** `401` for incorrect credentials; `423` for a temporarily locked account. MFA-enabled
accounts return the separate `202` MFA challenge flow, which is outside this core contract.

## 4. `GET /api/auth/me`

**200**

| Field | Type | Required | Notes |
|---|---|---:|---|
| `user` | object \| null | yes | `null` when there is no valid session |

Authenticated user fields:

| Field | Type | Required |
|---|---|---:|
| `id` | string | yes |
| `email` | string | yes |
| `role` | string | yes |
| `email_verified` | integer | yes |
| `plan` | string | yes |
| `upload_enabled` | integer | yes |
| `mfa_enabled` | integer | yes |
| `deleted_at` | string \| null | yes |
| `session_never_expires` | integer | yes |
| `session_created_at` | integer | yes |
| `last_seen_at` | integer | yes |

The snake_case fields are part of the current response shape; they are deliberately different from
the camelCase session user in `register`/`login`.

## 5. `POST /api/auth/logout`

**200**

| Field | Type | Required |
|---|---|---:|
| `signedOut` | boolean | yes |

The response also clears the session and CSRF cookies.

## 6. `GET /api/invitations`

**200 — array of invitation summaries**

| Field | Type | Required |
|---|---|---:|
| `id` | string | yes |
| `slug` | string | yes |
| `title` | string | yes |
| `type` | string | yes |
| `status` | string | yes |
| `archived` | boolean | yes |
| `views` | integer | yes |
| `rsvps` | integer | yes |
| `rsvpEnabled` | boolean | yes |
| `accessMode` | string | yes |
| `updatedAt` | integer | yes |
| `shared` | boolean | yes |
| `collaborationRole` | string \| null | yes |
| `preview` | object | yes |

**Preview object**

| Field | Type | Required |
|---|---|---:|
| `eventType` | string | yes |
| `theme` | string | yes |
| `accent` | string | yes |
| `palette` | object | yes |
| `fields` | object | yes |
| `objects` | object | yes |
| `designPages` | array | yes |
| `masterPageStyle` | object | yes |

**Errors:** `401` without a session; `400` when `limit`, `offset`, or `status` is invalid.

## 7. `POST /api/invitations`

Request: `{ "slug": string, "document": object }`.

**201**

| Field | Type | Required |
|---|---|---:|
| `id` | string | yes |
| `slug` | string | yes |
| `updatedAt` | integer | yes |

The server replaces whitespace/unsafe characters in the requested slug and appends a numeric suffix
when the slug is already taken.

**Errors:** `400` for a non-object document or malformed JSON; `401` without auth.

## 8. `GET /api/invitations/{id}`

**200**

| Field | Type | Required | Notes |
|---|---|---:|---|
| `id` | string | yes | |
| `slug` | string | yes | |
| `document` | object | yes | Stable core below; versioned extensions allowed |
| `updatedAt` | integer | yes | |
| `archived` | boolean | yes | |
| `accessMode` | string | yes | |
| `published` | boolean | yes | |
| `collaborationRole` | string \| null | yes | |
| `owner` | boolean | yes | |
| `lastClientId` | string \| null | yes | |
| `lastMutationId` | string \| null | yes | |
| `customDomain` | string | yes | |
| `publishAt` | integer \| null | yes | |
| `unpublishAt` | integer \| null | yes | |
| `expiresAt` | integer \| null | yes | |
| `galleryProtected` | boolean | yes | |

**Document stable core**

| Field | Type | Required |
|---|---|---:|
| `schemaVersion` | integer | yes |
| `eventType` | string | yes |
| `fields` | object | yes |
| `objects` | object | yes |
| `designPages` | array | yes |
| `settings` | object | yes |

**Errors:** `401` without auth; `404` for an unknown or unreadable invitation. A non-owner without
read access receives the same 404 shape, not an existence oracle.

## 9. `PUT /api/invitations/{id}`

Request: `{ "document": object, "expectedRevision"?: integer, "editReason"?: string }`.

**200**

| Field | Type | Required |
|---|---|---:|
| `saved` | boolean | yes |
| `updatedAt` | integer | yes |
| `clientId` | string \| null | yes |
| `mutationId` | string \| null | yes |
| `editedAfterSend` | boolean | yes |

**Errors:** `400` for a non-object document or invalid `expectedRevision`; `403` without edit access;
`404` for an unknown invitation; `409` with `code: "revision_conflict"` when the revision is stale.

## 10. `POST /api/invitations/{id}/publish`

Request: `{ "document"?: object, "expectedRevision"?: integer }`.

**201**

| Field | Type | Required |
|---|---|---:|
| `publicationId` | string | yes |
| `version` | integer | yes |
| `updatedAt` | integer | yes |
| `documentVersion` | integer | yes |
| `clientId` | string \| null | yes |
| `mutationId` | string \| null | yes |
| `slug` | string | yes |
| `url` | string | yes |

**Errors:** `401`; `403` without manage access; `404`; `409` for stale revisions or a policy gate.
Policy-gate errors additionally carry their documented readiness/code detail while retaining the
standard `error` field.

## 11. `DELETE /api/invitations/{id}`

**200**

| Field | Type | Required |
|---|---|---:|
| `deleted` | boolean | yes |

**Errors:** `401`; `404` for an unknown invitation or one the caller does not own.

## 12. `POST /api/invitations/{id}/guests`

Request: `{ "name": string, "phone"?: string, "email"?: string, "groupName"?: string,
"householdId"?: string, "tableName"?: string, "seatLabel"?: string, "tags"?: string[],
"linkExpiresDays"?: integer }`.

**201**

| Field | Type | Required |
|---|---|---:|
| `id` | string | yes |
| `name` | string | yes |
| `slug` | string | yes |
| `token` | string | yes |
| `tokenExpiresAt` | integer \| null | yes |

**Errors:** `400` when `name` is missing or a link expiration is invalid; `401`; `403` without
manage access.

## 13. `GET /api/invitations/{id}/guests`

**200 — array of guest records**

| Field | Type | Required |
|---|---|---:|
| `id` | string | yes |
| `name` | string | yes |
| `slug` | string | yes |
| `phone` | string | yes |
| `email` | string | yes |
| `group_name` | string | yes |
| `household_id` | string | yes |
| `tags` | string[] | yes |
| `table_name` | string | yes |
| `seat_label` | string | yes |
| `delivery_status` | string | yes |
| `opened_at` | integer \| null | yes |
| `token_salt` | string | yes |
| `token_version` | integer | yes |
| `token_expires_at` | integer \| null | yes |
| `token_revoked_at` | integer \| null | yes |
| `created_at` | integer | yes |
| `checked_in` | integer | yes |
| `checked_in_at` | integer \| null | yes |
| `rsvp_status` | string \| null | yes |
| `token` | string \| null | yes |
| `personalLinkAvailable` | boolean | yes |

**Errors:** `401`; `403` without manage access. The guest list is intentionally manager-only.

## 14. `PUT /api/invitations/{id}/guests/{guestId}/check-in`

Request: `{ "checkedIn": boolean }` (defaults to `true`).

**200**

| Field | Type | Required |
|---|---|---:|
| `checkedIn` | boolean | yes |
| `checkedInAt` | integer \| null | yes |
| `alreadyCheckedIn` | boolean | yes |

**Errors:** `401`; `403` without manage access; `404` when the guest does not exist in that
invitation.

## Standard error schema

Every tested 4xx response is JSON, not an HTML error page:

```json
{
  "error": "Human-readable message",
  "code": "optional_machine_code",
  "requestId": "optional_correlation_id"
}
```

- `error` — required string.
- `code` — optional string used by mutation/policy errors.
- `requestId` — optional additional correlation field; the authoritative correlation ID is always
  the `X-Request-ID` response header.
- Additional bounded detail fields are allowed (for example readiness data or revision metadata).

The contract test asserts JSON content type, `X-Request-ID`, the standard `error` field, and the
requested status for every error case.

## Fuzz cases covered

`tests/api_contract_test.py` sends these malformed or unauthorized requests and requires a structured
4xx JSON response, never a raw HTML 500 page:

- malformed JSON body (`{`);
- non-object invitation document;
- invalid `expectedRevision`;
- missing guest name;
- invalid invitation `limit` and `status` query values;
- missing registration fields;
- wrong login password;
- unauthenticated invitation list;
- unknown invitation, guest, and delete targets;
- foreign-account guest list and guest creation (`403`).

## Verification

```text
.venv/bin/python -m pytest tests/api_contract_test.py -q
# 2 passed
```

The suite is intentionally local-server based, so a schema change cannot pass against a mocked
handler that no longer matches `server.py`.

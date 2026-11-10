"""Privacy primitives shared by the HTTP handlers and the retention job.

This module deliberately has no dependency on ``server`` so the data-export,
erasure and retention rules can be tested without booting the HTTP server. All
database calls go through the caller-supplied ``connect`` context manager.
"""
from __future__ import annotations

import io
import json
import os
import re
import time
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Callable, Optional

PII_MARKER = "[REDACTED_PII]"
DAY_MS = 24 * 60 * 60 * 1000

# Emails and phone-like numbers are the stable PII markers in structured logs.
# The phone pattern deliberately does not match ISO dates or epoch timestamps.
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+\d{8,15}|\d{3}[\s.-]\d{3}[\s.-]\d{4}|\(\d{2,4}\)[\s.-]?\d{3}[\s.-]\d{4})(?!\d)")


def scrub_pii_text(value) -> str:
    """Return text safe for structured logs, preserving a redaction marker."""
    text = str(value or "")
    text = _EMAIL_RE.sub(PII_MARKER, text)
    return _PHONE_RE.sub(PII_MARKER, text)


def scrub_pii_value(value):
    """Recursively scrub a JSON-compatible value before it reaches a log."""
    if isinstance(value, dict):
        return {scrub_pii_text(key): scrub_pii_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub_pii_value(item) for item in value]
    if isinstance(value, str):
        return scrub_pii_text(value)
    return value


def _loads(value, default):
    try:
        parsed = json.loads(value or "")
    except (TypeError, ValueError):
        return default
    return parsed if isinstance(parsed, type(default)) else default


def _rows(db, sql, params=(), *, decode=()):
    result = []
    for row in db.execute(sql, params).fetchall():
        item = dict(row)
        for key, default in decode:
            if key in item:
                item[key[:-5] if key.endswith("_json") else key] = _loads(item.pop(key), default)
        result.append(item)
    return result


def _user_query(db, user_id):
    return db.execute(
        "SELECT id,email,role,plan,email_verified,upload_enabled,created_at,privacy_json "
        "FROM users WHERE id=? AND deleted_at IS NULL",
        (user_id,),
    ).fetchone()


def collect_account_export(connect, user_id: str) -> dict:
    """Collect every row owned by ``user_id`` into a JSON-safe export.

    The owner filter is applied before invitation-scoped tables are queried;
    an invitation id supplied by another account never enters the result.
    """
    with connect() as db:
        user = _user_query(db, user_id)
        if not user:
            raise ValueError("Account not found")
        invitations = _rows(
            db,
            "SELECT id,slug,draft_json,updated_at,archived,views,access_mode,is_published,"
            "publish_at,unpublish_at,expires_at FROM invitations "
            "WHERE owner_id=? AND deleted_at IS NULL ORDER BY updated_at DESC",
            (user_id,),
            decode=(("draft_json", {}),),
        )
        invite_ids = [row["id"] for row in invitations]
        publications = rsvps = guests = wishes = assets = deliveries = comments = campaigns = []
        message_deliveries = signup_claims = gift_claims = poll_votes = album_photos = approval_requests = []
        if invite_ids:
            marks = ",".join("?" for _ in invite_ids)
            publications = _rows(db, f"SELECT * FROM publications WHERE invitation_id IN ({marks})", invite_ids,
                                 decode=(("document_json", {}),))
            rsvps = _rows(db, f"SELECT * FROM rsvps WHERE invitation_id IN ({marks})", invite_ids,
                          decode=(("answers_json", {}),))
            guests = _rows(db, f"SELECT * FROM guests WHERE invitation_id IN ({marks})", invite_ids,
                           decode=(("tags_json", []),))
            wishes = _rows(db, f"SELECT * FROM guest_messages WHERE invitation_id IN ({marks})", invite_ids)
            assets = _rows(db, f"SELECT * FROM assets WHERE invitation_id IN ({marks})", invite_ids,
                           decode=(("tags_json", []),))
            deliveries = _rows(db, f"SELECT * FROM delivery_attempts WHERE invitation_id IN ({marks})", invite_ids,
                               decode=(("metadata_json", {}),))
            comments = _rows(db, f"SELECT * FROM invitation_comments WHERE invitation_id IN ({marks})", invite_ids)
            campaigns = _rows(db, f"SELECT * FROM message_campaigns WHERE invitation_id IN ({marks})", invite_ids,
                              decode=(("segment_json", {}),))
            message_deliveries = _rows(
                db,
                f"SELECT d.* FROM message_deliveries d JOIN message_campaigns c ON c.id=d.campaign_id "
                f"WHERE c.invitation_id IN ({marks})",
                invite_ids,
            )
            signup_claims = _rows(
                db,
                f"SELECT c.* FROM signup_claims c JOIN signup_sheets s ON s.id=c.sheet_id "
                f"WHERE s.invitation_id IN ({marks})",
                invite_ids,
            )
            gift_claims = _rows(
                db,
                f"SELECT c.* FROM gift_registry_claims c JOIN gift_registry_items i ON i.id=c.item_id "
                f"WHERE i.invitation_id IN ({marks})",
                invite_ids,
            )
            poll_votes = _rows(
                db,
                f"SELECT v.* FROM poll_votes v JOIN polls p ON p.id=v.poll_id "
                f"WHERE p.invitation_id IN ({marks})",
                invite_ids,
            )
            album_photos = _rows(db, f"SELECT * FROM album_photos WHERE invitation_id IN ({marks})", invite_ids)
            approval_requests = _rows(db, f"SELECT * FROM approval_requests WHERE invitation_id IN ({marks})", invite_ids,
                                      decode=(("summary_json", {}),))
        templates = _rows(db, "SELECT * FROM user_templates WHERE owner_id=? ORDER BY updated_at DESC", (user_id,),
                          decode=(("document_json", {}), ("thumbnail_json", {})))
        page_templates = _rows(db, "SELECT * FROM user_page_templates WHERE owner_id=? ORDER BY updated_at DESC", (user_id,),
                                decode=(("page_json", {}),))
        components = _rows(db, "SELECT * FROM user_components WHERE owner_id=? ORDER BY updated_at DESC", (user_id,),
                           decode=(("payload_json", {}),))
        studio_resources = _rows(db, "SELECT * FROM studio_resources WHERE owner_id=? ORDER BY updated_at DESC", (user_id,),
                                 decode=(("payload_json", {}), ("governance_json", {})))
        studio_releases = _rows(db, "SELECT * FROM studio_releases WHERE owner_id=? ORDER BY updated_at DESC", (user_id,),
                                decode=(("manifest_json", []),))
        studio_pins = _rows(
            db,
            "SELECT p.* FROM invitation_studio_release_pins p JOIN invitations i ON i.id=p.invitation_id "
            "WHERE i.owner_id=?",
            (user_id,),
        )
        governance = db.execute("SELECT policy_json,updated_at FROM studio_governance WHERE owner_id=?", (user_id,)).fetchone()
        backup_policy = db.execute("SELECT * FROM studio_backup_policies WHERE owner_id=?", (user_id,)).fetchone()
        bulk_jobs = _rows(db, "SELECT * FROM studio_bulk_jobs WHERE owner_id=? ORDER BY created_at DESC LIMIT 100", (user_id,),
                          decode=(("selection_json", {}), ("result_json", {})))
        account = dict(user)
        account["emailVerified"] = bool(account.pop("email_verified", 0))
        account["uploadEnabled"] = bool(account.pop("upload_enabled", 1))
        account["privacy"] = _loads(account.pop("privacy_json", "{}"), {})
    return {
        "schema": "einvite-privacy-export-v1",
        "exportedAt": int(time.time() * 1000),
        "account": account,
        "invitations": invitations,
        "publications": publications,
        "rsvps": rsvps,
        "guests": guests,
        "wishes": wishes,
        "assets": assets,
        "deliveryAttempts": deliveries,
        "comments": comments,
        "campaigns": campaigns,
        "messageDeliveries": message_deliveries,
        "signupClaims": signup_claims,
        "giftRegistryClaims": gift_claims,
        "pollVotes": poll_votes,
        "albumPhotos": album_photos,
        "approvalRequests": approval_requests,
        "templates": templates,
        "pageTemplates": page_templates,
        "components": components,
        "studioResources": studio_resources,
        "studioReleases": studio_releases,
        "studioReleasePins": studio_pins,
        "studioGovernance": _loads(governance["policy_json"], {}) if governance else {},
        "studioBackupPolicy": dict(backup_policy) if backup_policy else {},
        "studioBulkJobs": bulk_jobs,
    }


def build_export_archive(export: dict) -> bytes:
    """Build the downloadable ZIP without any filesystem-side state."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("account.json", json.dumps(export, ensure_ascii=False, indent=2))
        archive.writestr("README.txt", "eInvite privacy export. Keep this archive private.\n")
    return buffer.getvalue()


def _parse_event_datetime(raw_date: str, raw_time: str):
    for value, pattern in ((f"{raw_date[:10]} {raw_time}", "%Y-%m-%d %H:%M"),
                           (raw_date[:10], "%Y-%m-%d")):
        try:
            return datetime.strptime(value, pattern).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _event_expiry_ms(row):
    expires = row.get("expires_at")
    if not expires:
        return None
    try:
        return int(expires)
    except (TypeError, ValueError):
        return None


def _event_fields(row):
    document = _loads(row.get("draft_json"), {})
    return document.get("fields") if isinstance(document, dict) else {}


def _event_end_ms(row, now_ms: int) -> Optional[int]:
    expires = _event_expiry_ms(row)
    if expires is not None:
        return expires
    fields = _event_fields(row)
    raw_date = str((fields or {}).get("date") or "").strip()
    if not raw_date:
        return None
    raw_time = str((fields or {}).get("time") or "23:59").strip()[:5]
    date = _parse_event_datetime(raw_date, raw_time)
    if date is None:
        return None
    if raw_time == "23:59":
        date = date.replace(hour=23, minute=59, second=59)
    return int(date.timestamp() * 1000)


def _public_or_past(row, now_ms: int) -> bool:
    if int(row.get("is_published") or 0) or int(row.get("archived") or 0):
        return True
    ends = _event_end_ms(row, now_ms)
    return ends is not None and ends <= now_ms


def anonymize_invitation_pii(db, invitation_id: str, now_ms: int) -> dict:
    """Replace guest PII while retaining RSVP statistics and event content."""
    guests = db.execute(
        "SELECT id FROM guests WHERE invitation_id=? ORDER BY created_at,id", (invitation_id,)
    ).fetchall()
    names = {}
    for index, row in enumerate(guests, start=1):
        label = f"Guest {index}"
        names[row["id"]] = label
        db.execute(
            "UPDATE guests SET name=?,phone='',email='',group_name='',household_id='',"
            "tags_json='[]',table_name='',seat_label='',slug='',token=?,token_hash=NULL,"
            "token_salt='',token_version=token_version+1,token_revoked_at=?,"
            "delivery_status='not-sent',opened_at=NULL WHERE id=?",
            (label, uuid.uuid4().hex, now_ms, row["id"]),
        )
    rsvps = db.execute("SELECT id,guest_id FROM rsvps WHERE invitation_id=?", (invitation_id,)).fetchall()
    for index, row in enumerate(rsvps, start=1):
        label = names.get(row["guest_id"]) or f"Guest {index}"
        db.execute(
            "UPDATE rsvps SET name=?,normalized_name=?,note=?,answers_json='{}' WHERE id=?",
            (label, label.lower(), PII_MARKER, row["id"]),
        )
    db.execute("UPDATE guest_messages SET name=?,message=? WHERE invitation_id=?", ("Guest", PII_MARKER, invitation_id))
    db.execute("UPDATE delivery_attempts SET recipient=?,error='',metadata_json='{}' WHERE invitation_id=?",
               (PII_MARKER, invitation_id))
    db.execute("UPDATE message_campaigns SET message=?,segment_json='{}' WHERE invitation_id=?",
               (PII_MARKER, invitation_id))
    db.execute("UPDATE album_photos SET uploader_email='',uploader_guest_id=NULL WHERE invitation_id=?",
               (invitation_id,))
    db.execute(
        "UPDATE signup_claims SET email='',name='',guest_id=NULL WHERE sheet_id IN "
        "(SELECT id FROM signup_sheets WHERE invitation_id=?)",
        (invitation_id,),
    )
    db.execute(
        "UPDATE gift_registry_claims SET email='',name='',guest_id=NULL WHERE item_id IN "
        "(SELECT id FROM gift_registry_items WHERE invitation_id=?)",
        (invitation_id,),
    )
    db.execute(
        "UPDATE poll_votes SET email='',name='',guest_id=NULL WHERE poll_id IN "
        "(SELECT id FROM polls WHERE invitation_id=?)",
        (invitation_id,),
    )
    db.execute("UPDATE analytics_events SET payload_json='{}' WHERE invitation_id=?", (invitation_id,))
    db.execute("UPDATE approval_requests SET note=?,summary_json='{}' WHERE invitation_id=?",
               (PII_MARKER, invitation_id))
    db.execute("DELETE FROM review_notifications WHERE invitation_id=?", (invitation_id,))
    db.execute(
        "UPDATE message_deliveries SET error='' WHERE campaign_id IN "
        "(SELECT id FROM message_campaigns WHERE invitation_id=?)",
        (invitation_id,),
    )
    try:
        db.execute("DELETE FROM outbound_retry_queue WHERE invitation_id=?", (invitation_id,))
    except Exception:
        # The queue is created lazily on the first outbound failure.
        pass
    return {"guests": len(guests), "rsvps": len(rsvps)}


def run_pii_retention(connect, retention_days: Optional[int] = None, now_ms: Optional[int] = None) -> dict:
    """Anonymize guest PII for events whose end is older than the window."""
    now = int(now_ms if now_ms is not None else time.time() * 1000)
    if retention_days is None:
        try:
            retention_days = int(os.environ.get("EINVITE_PII_RETENTION_DAYS", "90"))
        except (TypeError, ValueError):
            retention_days = 90
    days = max(1, min(3650, int(retention_days)))
    cutoff = now - days * DAY_MS
    rows = []
    with connect() as db:
        for row in db.execute(
            "SELECT id,draft_json,expires_at,is_published,archived FROM invitations "
            "WHERE deleted_at IS NULL"
        ).fetchall():
            ends = _event_end_ms(dict(row), now)
            if ends is not None and ends < cutoff:
                rows.append(dict(row))
        guest_count = rsvp_count = 0
        for row in rows:
            counts = anonymize_invitation_pii(db, row["id"], now)
            guest_count += counts["guests"]
            rsvp_count += counts["rsvps"]
    return {
        "retentionDays": days,
        "cutoff": cutoff,
        "anonymizedInvitations": len(rows),
        "anonymizedGuests": guest_count,
        "anonymizedRsvps": rsvp_count,
    }


def _anonymize_account_invitations(db, invitations, now):
    deleted_invitations = anonymized_invitations = 0
    for invitation in invitations:
        anonymize_invitation_pii(db, invitation["id"], now)
        if _public_or_past(invitation, now):
            anonymized_invitations += 1
        else:
            deleted_invitations += 1
            db.execute(
                "UPDATE invitations SET deleted_at=?,purge_at=?,draft_json=?,slug=?,"
                "is_published=0,archived=1,custom_domain=NULL,gallery_access_password_hash=NULL,"
                "gallery_access_password_salt=NULL,access_password_hash=NULL,access_password_salt=NULL "
                "WHERE id=?",
                (now, now, json.dumps({"fields": {}, "objects": {}, "designPages": [], "settings": {}}),
                 f"deleted-{uuid.uuid4().hex}", invitation["id"]),
            )
    return deleted_invitations, anonymized_invitations


def _delete_account_platform_rows(db, user_id):
    for table in ("user_templates", "user_page_templates", "user_components", "studio_resources",
                  "studio_releases", "invitation_studio_release_pins", "studio_governance",
                  "studio_backup_policies", "studio_bulk_jobs"):
        db.execute(f"DELETE FROM {table} WHERE owner_id=?", (user_id,))
    # Platform/job/backup metadata can contain request payloads, backup
    # manifests or account identifiers. Remove it as part of the confirmed
    # erasure rather than leaving a second copy outside the guest tables.
    for table, column in (("platform_jobs", "owner_id"), ("privacy_requests", "user_id"),
                          ("idempotency_records", "user_id"), ("deleted_items", "owner_id"),
                          ("ai_memories", "user_id"), ("ai_knowledge_sources", "user_id"),
                          ("ai_plans", "user_id"), ("platform_backups", "owner_id"),
                          ("workspace_memberships", "user_id"), ("upload_sessions", "owner_id"),
                          ("review_notifications", "user_id")):
        try:
            db.execute(f"DELETE FROM {table} WHERE {column}=?", (user_id,))
        except Exception:
            # Optional platform tables exist only after their feature is used.
            pass


def _delete_account_ai_data(db, user_id):
    try:
        conversations = [row["id"] for row in db.execute(
            "SELECT id FROM ai_conversations WHERE user_id=?", (user_id,)).fetchall()]
        if conversations:
            marks = ",".join("?" for _ in conversations)
            db.execute(f"DELETE FROM ai_messages WHERE conversation_id IN ({marks})", conversations)
        db.execute("DELETE FROM ai_conversations WHERE user_id=?", (user_id,))
    except Exception:
        pass


def _soft_delete_account_workspaces(db, user_id, now):
    try:
        db.execute("UPDATE workspaces SET name='Deleted workspace',settings_json='{}',deleted_at=?,updated_at=? WHERE owner_id=?",
                   (now, now, user_id))
    except Exception:
        pass


def _delete_account_queues(db, invite_ids):
    if not invite_ids:
        return
    marks = ",".join("?" for _ in invite_ids)
    for sql in (f"DELETE FROM outbound_retry_queue WHERE invitation_id IN ({marks})",
                f"DELETE FROM message_deliveries WHERE campaign_id IN "
                f"(SELECT id FROM message_campaigns WHERE invitation_id IN ({marks}))",
                f"DELETE FROM review_notifications WHERE invitation_id IN ({marks})"):
        try:
            db.execute(sql, invite_ids)
        except Exception:
            pass


def _delete_account_identity(db, user_id, now):
    for table in ("sessions", "auth_tokens", "mfa_recovery_codes", "passkeys", "api_keys"):
        try:
            db.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        except Exception:
            # Older databases may predate an optional auth table; the
            # tombstone and deleted_at still block all login paths.
            pass
    db.execute("DELETE FROM invitation_collaborators WHERE user_id=?", (user_id,))
    db.execute("UPDATE invitation_comments SET body=? WHERE user_id=?", (PII_MARKER, user_id))
    try:
        db.execute("UPDATE stored_objects SET deleted_at=?,ref_count=0 WHERE owner_id=?", (now, user_id))
    except Exception:
        pass
    # Redact PII that may have been copied into audit metadata, while
    # retaining the action/timestamp evidence required for accountability.
    for row in db.execute("SELECT id,metadata_json FROM audit_events WHERE user_id=?", (user_id,)).fetchall():
        db.execute("UPDATE audit_events SET metadata_json=? WHERE id=?",
                   (json.dumps(scrub_pii_value(_loads(row["metadata_json"], {})), ensure_ascii=False), row["id"]))
    deleted_email = f"deleted-{uuid.uuid4().hex}@invalid"
    db.execute(
        "UPDATE users SET email=?,email_hash=NULL,password_hash=?,salt=?,deleted_at=?,"
        "deletion_scheduled_at=NULL,privacy_json='{}',studio_name='',white_label_json='{}',"
        "stripe_customer_id=NULL,stripe_subscription_id=NULL,upload_enabled=0 WHERE id=?",
        (deleted_email, "!deleted-" + uuid.uuid4().hex, uuid.uuid4().hex, now, user_id),
    )


def delete_account_data(connect, user_id: str, now_ms: Optional[int] = None) -> dict:
    """Soft-delete an account and irreversibly anonymize its guest records.

    The password/CSRF confirmation happens in the HTTP handler before this
    function is called. The user row is retained as a tombstone so foreign
    keys and audit records remain valid, but its credentials, email and
    profile data are shredded and ``deleted_at`` prevents every login path.
    """
    now = int(now_ms if now_ms is not None else time.time() * 1000)
    with connect() as db:
        user = db.execute("SELECT id,email FROM users WHERE id=? AND deleted_at IS NULL", (user_id,)).fetchone()
        if not user:
            raise ValueError("Account not found")
        invitations = [dict(row) for row in db.execute(
            "SELECT id,is_published,archived,expires_at,draft_json FROM invitations WHERE owner_id=?",
            (user_id,),
        ).fetchall()]
        deleted_invitations, anonymized_invitations = _anonymize_account_invitations(db, invitations, now)
        _delete_account_platform_rows(db, user_id)
        _delete_account_ai_data(db, user_id)
        _soft_delete_account_workspaces(db, user_id, now)
        _delete_account_queues(db, [str(invitation["id"]) for invitation in invitations])
        _delete_account_identity(db, user_id, now)
    return {
        "deleted": True,
        "loginDisabled": True,
        "deletedInvitations": deleted_invitations,
        "anonymizedInvitations": anonymized_invitations,
        "deletedTemplates": True,
    }

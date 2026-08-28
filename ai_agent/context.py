"""Authorized, bounded and redacted project context builder."""
from __future__ import annotations
import hashlib
import json
from typing import Any, Callable


SECRET_KEYS = {"token", "password", "secret", "cookie", "authorization", "apiKey", "accessToken", "csrf", "signedUrl"}
DERIVED_KEYS = {"domGeometry", "renderBounds", "selectionRect", "computedStyle", "layoutCache"}


def _clone_bounded(value: Any, depth: int = 0) -> Any:
    if depth > 8:
        return "[bounded]"
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            if str(key) in SECRET_KEYS or str(key) in DERIVED_KEYS:
                continue
            result[str(key)[:120]] = _clone_bounded(child, depth + 1)
        return result
    if isinstance(value, list):
        return [_clone_bounded(item, depth + 1) for item in value[:300]]
    if isinstance(value, str):
        return value[:50_000]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:1000]


def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: canonical(value[key]) for key in sorted(value) if key not in DERIVED_KEYS and key not in {"updatedAt", "selectionIds"}}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def fingerprint(value: Any) -> str:
    encoded = json.dumps(canonical(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return "sha256-" + hashlib.sha256(encoded).hexdigest()


def _plain_text(obj: dict[str, Any]) -> str:
    if isinstance(obj.get("text"), str):
        return obj["text"][:5000]
    paragraphs = ((obj.get("richText") or {}).get("paragraphs") or [])
    parts = []
    for paragraph in paragraphs[:100]:
        parts.append("".join(str(run.get("text", "")) for run in (paragraph.get("runs") or [])[:200]))
    return "\n".join(parts)[:5000]


def _object_summary(object_id: str, obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": object_id,
        "type": str(obj.get("type") or obj.get("objectType") or "text")[:30],
        "text": _plain_text(obj),
        "alt": str(obj.get("alt") or "")[:1000],
        "left": obj.get("left"), "top": obj.get("top"), "width": obj.get("width"), "height": obj.get("height"),
        "rotation": obj.get("rotation", 0), "visible": obj.get("visible", True), "locked": obj.get("locked", False),
        "textStyleId": obj.get("textStyleId"), "fontPairing": obj.get("fontPairing"), "fontSize": obj.get("fontSize"), "color": obj.get("color"),
        "groupId": obj.get("groupId") or obj.get("parentGroupId") or "",
    }


def _page_maps(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pages = {"hero": document.get("objects") or {}}
    for page in document.get("designPages") or []:
        page_id = str(page.get("id") or "")
        if page_id:
            pages[f"page:{page_id}"] = page.get("objects") or {}
    return pages


class ContextError(ValueError):
    pass


class ContextBuilder:
    def __init__(self, connect: Callable[[], Any], max_bytes: int = 180_000):
        self.connect = connect
        self.max_bytes = max_bytes

    def build(self, invitation_id: str, user_id: str, role: str, client_context: dict[str, Any] | None = None) -> dict[str, Any]:
        client_context = client_context if isinstance(client_context, dict) else {}
        include_operations = bool(client_context.get("includeOperationalData"))
        with self.connect() as db:
            row = db.execute("SELECT id,slug,draft_json,updated_at,is_published,owner_id,views,custom_domain,publish_at,unpublish_at,expires_at FROM invitations WHERE id=? AND deleted_at IS NULL", (invitation_id,)).fetchone()
            if not row:
                raise ContextError("Invitation not found")
            asset_rows = db.execute("SELECT id,name,mime,path,width,height,folder,tags_json,favorite FROM assets WHERE invitation_id=? ORDER BY created_at DESC LIMIT 100", (invitation_id,)).fetchall()
            review = db.execute("SELECT COUNT(*) total,SUM(CASE WHEN resolved=0 THEN 1 ELSE 0 END) open_count FROM invitation_comments WHERE invitation_id=?", (invitation_id,)).fetchone()
            guest_rows = db.execute("SELECT id,name,group_name,table_name,seat_label,checked_in,delivery_status FROM guests WHERE invitation_id=? ORDER BY created_at DESC LIMIT 200", (invitation_id,)).fetchall() if include_operations else []
            rsvp_rows = db.execute("SELECT id,guest_id,name,status,guest_count,created_at FROM rsvps WHERE invitation_id=? ORDER BY created_at DESC LIMIT 200", (invitation_id,)).fetchall() if include_operations else []
        try:
            document = json.loads(row["draft_json"] or "{}")
        except Exception as exc:
            raise ContextError("Invitation document is invalid") from exc
        document = _clone_bounded(document)
        maps = _page_maps(document)
        page_id = str(client_context.get("pageId") or client_context.get("canvasId") or "hero")[:120]
        if page_id not in maps:
            raise ContextError("Referenced page does not exist")
        selected_ids = [str(item) for item in (client_context.get("objectIds") or client_context.get("targetObjectIds") or [])][:100]
        missing = [object_id for object_id in selected_ids if object_id not in maps[page_id]]
        if missing:
            raise ContextError("Referenced selection contains unknown object IDs")
        selected = [_object_summary(object_id, maps[page_id][object_id]) for object_id in selected_ids]
        page_summaries = [{"id": "hero", "name": "Hero", "objectCount": len(maps["hero"]), "enabled": True}]
        for page in (document.get("designPages") or [])[:100]:
            page_summaries.append({"id": f"page:{page.get('id')}", "name": str(page.get("name") or "Page")[:160], "objectCount": len(page.get("objects") or {}), "enabled": page.get("enabled", True)})
        assets = []
        for asset in asset_rows:
            try:
                tags = json.loads(asset["tags_json"] or "[]")
            except Exception:
                tags = []
            assets.append({"id": asset["id"], "name": str(asset["name"] or "")[:200], "mime": asset["mime"], "width": asset["width"], "height": asset["height"], "folder": str(asset["folder"] or "")[:120], "tags": tags[:20], "favorite": bool(asset["favorite"])})
        result = {
            "invitation": {"id": row["id"], "slug": row["slug"], "revision": int(row["updated_at"] or 0), "fingerprint": fingerprint(document), "published": bool(row["is_published"]), "role": role},
            "document": {
                "eventType": document.get("eventType"), "fields": document.get("fields") or {}, "settings": document.get("settings") or {},
                "palette": document.get("palette") or {}, "accent": document.get("accent"), "brandKitId": document.get("brandKitId") or document.get("brandKit"),
                "pageSummaries": page_summaries, "activePageId": page_id, "selection": selected,
                "reviewStatus": {"totalComments": int((review or {})["total"] or 0), "openComments": int((review or {})["open_count"] or 0)} if review else {"totalComments": 0, "openComments": 0},
            },
            "assets": assets,
            "operations": {
                "included": include_operations,
                "views": int(row["views"] or 0),
                "customDomain": str(row["custom_domain"] or "")[:253],
                "publishAt": row["publish_at"], "unpublishAt": row["unpublish_at"], "expiresAt": row["expires_at"],
                "guests": [{"id": item["id"], "name": str(item["name"] or "")[:120], "groupName": str(item["group_name"] or "")[:80], "tableName": str(item["table_name"] or "")[:80], "seatLabel": str(item["seat_label"] or "")[:40], "checkedIn": bool(item["checked_in"]), "deliveryStatus": str(item["delivery_status"] or "")[:40]} for item in guest_rows],
                "rsvps": [{"id": item["id"], "guestId": str(item["guest_id"] or ""), "name": str(item["name"] or "")[:120], "status": str(item["status"] or "")[:40], "guestCount": int(item["guest_count"] or 1), "createdAt": int(item["created_at"] or 0)} for item in rsvp_rows],
            },
            "references": _clone_bounded(client_context.get("references") or {}),
            "attachments": _clone_bounded(client_context.get("attachmentDescriptors") or []),
        }
        encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > self.max_bytes:
            result["assets"] = result["assets"][:20]
            result["operations"]["guests"] = result["operations"]["guests"][:50]
            result["operations"]["rsvps"] = result["operations"]["rsvps"][:50]
            result["document"]["fields"] = {key: str(value)[:2000] for key, value in list((result["document"]["fields"] or {}).items())[:30]}
            encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > self.max_bytes:
            result["document"]["selection"] = result["document"]["selection"][:20]
            result["contextTruncated"] = True
        return result

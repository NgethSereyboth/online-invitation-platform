"""Typed V28 tool registry and strict validation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import copy
import json
import re


class ToolValidationError(ValueError):
    def __init__(self, message: str, code: str = "invalid_tool_arguments"):
        super().__init__(message)
        self.code = code


FORBIDDEN_KEYS = {
    "selector", "css", "html", "sql", "script", "javascript", "code", "filesystem",
    "filePath", "path", "network", "destination", "endpoint", "url", "command", "shell",
}
FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"javascript\s*:", re.I),
    re.compile(r"(?:file|ftp|data)://", re.I),
    re.compile(r"<\s*(?:script|iframe|object|embed)\b", re.I),
    re.compile(r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)\s+", re.I),
    re.compile(r"(?:^|[\s;&|])(?:bash|sh|cmd|powershell|python|node)\s+-", re.I),
)
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
GEOMETRY_RE = re.compile(r"^-?\d+(?:\.\d+)?(?:%|px)$")


@dataclass(frozen=True)
class ToolDefinition:
    id: str
    description: str
    risk: str
    permission: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    reversible: bool = True
    confirmation: bool = False
    executor: str = "client"

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "risk": self.risk,
            "permission": self.permission,
            "inputSchema": copy.deepcopy(self.input_schema),
            "outputSchema": copy.deepcopy(self.output_schema),
            "reversible": self.reversible,
            "confirmationRequired": self.confirmation,
            "executor": self.executor,
        }


def obj(properties: dict[str, Any], required: list[str] | None = None, additional: bool = False) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or [], "additionalProperties": additional}


def arr(items: dict[str, Any], maximum: int = 100) -> dict[str, Any]:
    return {"type": "array", "items": items, "maxItems": maximum}


def string(maximum: int = 50_000, enum: list[str] | None = None, fmt: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "string", "maxLength": maximum}
    if enum is not None:
        value["enum"] = enum
    if fmt:
        value["format"] = fmt
    return value


def number(minimum: float = -1e9, maximum: float = 1e9) -> dict[str, Any]:
    return {"type": "number", "minimum": minimum, "maximum": maximum}


ID = string(120, fmt="stable-id")
IDS = arr(ID, 100)
TEXT = string(50_000)
GEOMETRY = string(32, fmt="geometry")
COLOR = string(7, fmt="hex-color")


def _defs() -> list[ToolDefinition]:
    low = "low"
    medium = "medium"
    high = "high"
    edit = "edit"
    read = "read"
    manage = "manage"
    return [
        ToolDefinition("read.project_summary", "Read a bounded invitation summary.", low, read, obj({}), obj({"summary": obj({}, additional=True)}), executor="server"),
        ToolDefinition("read.page_summary", "Read one page summary by stable page ID.", low, read, obj({"pageId": ID}, ["pageId"]), obj({"page": obj({}, additional=True)}), executor="server"),
        ToolDefinition("read.selection_summary", "Read the captured selection summary.", low, read, obj({"objectIds": IDS}), obj({"selection": arr(obj({}, additional=True))}), executor="server"),
        ToolDefinition("selection.select_layers", "Select layers by stable IDs.", low, edit, obj({"objectIds": IDS}, ["objectIds"]), obj({"selectedIds": IDS})),
        ToolDefinition("object.create_text", "Create a text object.", low, edit, obj({"pageId": ID, "text": TEXT, "style": obj({}, additional=True)}, ["pageId", "text"]), obj({"createdIds": IDS})),
        ToolDefinition("object.create_image", "Create an image object from an existing authorized asset.", medium, edit, obj({"pageId": ID, "assetId": ID, "alt": string(1000), "geometry": obj({}, additional=True)}, ["pageId", "assetId", "alt"]), obj({"createdIds": IDS})),
        ToolDefinition("object.create_shape", "Create a bounded shape object.", low, edit, obj({"pageId": ID, "shape": string(30, ["rectangle", "ellipse", "line"]), "fill": COLOR, "geometry": obj({}, additional=True)}, ["pageId", "shape", "fill"]), obj({"createdIds": IDS})),
        ToolDefinition("object.update", "Update allowed object properties.", low, edit, obj({"pageId": ID, "objectIds": IDS, "patch": obj({}, additional=True)}, ["pageId", "objectIds", "patch"]), obj({"updatedIds": IDS})),
        ToolDefinition("object.duplicate", "Duplicate selected objects.", low, edit, obj({"pageId": ID, "objectIds": IDS}, ["pageId", "objectIds"]), obj({"createdIds": IDS})),
        ToolDefinition("object.delete", "Delete project-local objects.", high, edit, obj({"pageId": ID, "objectIds": IDS}, ["pageId", "objectIds"]), obj({"deletedIds": IDS}), confirmation=True),
        ToolDefinition("rich_text.replace", "Replace structured rich text while preserving declared semantics.", low, edit, obj({"pageId": ID, "objectIds": IDS, "text": TEXT, "mode": string(30, ["preserve", "preserve-leading-format", "replace-plain"])}, ["pageId", "objectIds", "text", "mode"]), obj({"updatedIds": IDS})),
        ToolDefinition("transform.move", "Move objects using document geometry.", low, edit, obj({"pageId": ID, "objectIds": IDS, "left": GEOMETRY, "top": GEOMETRY}, ["pageId", "objectIds", "left", "top"]), obj({"updatedIds": IDS})),
        ToolDefinition("transform.resize", "Resize objects using document geometry.", low, edit, obj({"pageId": ID, "objectIds": IDS, "width": GEOMETRY, "height": GEOMETRY}, ["pageId", "objectIds", "width", "height"]), obj({"updatedIds": IDS})),
        ToolDefinition("transform.rotate", "Rotate objects.", low, edit, obj({"pageId": ID, "objectIds": IDS, "degrees": number(-360, 360)}, ["pageId", "objectIds", "degrees"]), obj({"updatedIds": IDS})),
        ToolDefinition("transform.align", "Align objects on an axis.", low, edit, obj({"pageId": ID, "objectIds": IDS, "alignment": string(30, ["left", "center", "right", "top", "middle", "bottom"])}, ["pageId", "objectIds", "alignment"]), obj({"updatedIds": IDS})),
        ToolDefinition("transform.distribute", "Distribute objects evenly.", low, edit, obj({"pageId": ID, "objectIds": IDS, "axis": string(20, ["horizontal", "vertical"])}, ["pageId", "objectIds", "axis"]), obj({"updatedIds": IDS})),
        ToolDefinition("transform.tidy", "Arrange objects into a tidy bounded grid.", medium, edit, obj({"pageId": ID, "objectIds": IDS, "columns": number(1, 12), "gap": number(0, 200)}, ["pageId", "objectIds"]), obj({"updatedIds": IDS})),
        ToolDefinition("transform.group", "Group two or more objects.", low, edit, obj({"pageId": ID, "objectIds": IDS, "name": string(100)}, ["pageId", "objectIds"]), obj({"groupIds": IDS})),
        ToolDefinition("transform.ungroup", "Ungroup objects.", low, edit, obj({"pageId": ID, "objectIds": IDS}, ["pageId", "objectIds"]), obj({"groupIds": IDS})),
        ToolDefinition("transform.arrange", "Change layer order.", low, edit, obj({"pageId": ID, "objectIds": IDS, "position": string(20, ["front", "back", "forward", "backward"])}, ["pageId", "objectIds", "position"]), obj({"updatedIds": IDS})),
        ToolDefinition("style.apply_text_style", "Apply a semantic text style.", low, edit, obj({"pageId": ID, "objectIds": IDS, "styleId": ID}, ["pageId", "objectIds", "styleId"]), obj({"updatedIds": IDS})),
        ToolDefinition("style.apply_palette", "Apply a bounded invitation palette.", medium, edit, obj({"colors": arr(COLOR, 4)}, ["colors"]), obj({"updated": string(30)})),
        ToolDefinition("style.apply_brand_kit", "Apply an existing authorized brand kit by ID.", medium, edit, obj({"brandKitId": ID}, ["brandKitId"]), obj({"updated": string(30)})),
        ToolDefinition("style.apply_photo", "Apply a non-destructive photo style.", low, edit, obj({"pageId": ID, "objectIds": IDS, "preset": string(40)}, ["pageId", "objectIds", "preset"]), obj({"updatedIds": IDS})),
        ToolDefinition("image.configure_frame", "Configure frame, fit, mask, and focal position for authorized image layers.", low, edit, obj({"pageId": ID, "objectIds": IDS, "frame": string(20, ["none", "white", "gold", "dark"]), "fit": string(20, ["cover", "contain"]), "mask": string(30, ["none", "circle", "arch", "rounded"]), "positionX": number(0, 100), "positionY": number(0, 100), "borderRadius": number(0, 200)}, ["pageId", "objectIds"]), obj({"updatedIds": IDS})),
        ToolDefinition("gallery.arrange", "Arrange selected image layers into a bounded gallery grid.", medium, edit, obj({"pageId": ID, "objectIds": IDS, "columns": number(1, 12), "gap": number(0, 200)}, ["pageId", "objectIds"]), obj({"updatedIds": IDS})),
        ToolDefinition("photo.remove_background", "Run the existing bounded local background-removal workflow for one authorized image layer.", medium, edit, obj({"pageId": ID, "objectIds": IDS}, ["pageId", "objectIds"]), obj({"updatedIds": IDS, "materialCreated": {"type": "boolean"}}), confirmation=True),
        ToolDefinition("page.create", "Create an invitation page.", medium, edit, obj({"name": string(100), "templateId": ID}, ["name"]), obj({"createdPageIds": IDS})),
        ToolDefinition("page.duplicate", "Duplicate an existing page.", medium, edit, obj({"pageId": ID, "name": string(100)}, ["pageId"]), obj({"createdPageIds": IDS})),
        ToolDefinition("page.rename", "Rename an invitation page.", low, edit, obj({"pageId": ID, "name": string(100)}, ["pageId", "name"]), obj({"updatedPageIds": IDS})),
        ToolDefinition("page.reorder", "Reorder invitation pages.", medium, edit, obj({"pageIds": IDS}, ["pageIds"]), obj({"updatedPageIds": IDS})),
        ToolDefinition("page.configure_style", "Configure page background, entrance animation, and transition using bounded page properties.", medium, edit, obj({"pageId": ID, "background": COLOR, "backgroundAssetId": ID, "clearBackgroundImage": {"type":"boolean"}, "backgroundSize": string(20, ["cover", "contain"]), "backgroundOverlay": number(0, 80), "useMasterBackground": {"type":"boolean"}, "animationPreset": string(30, ["fade-up", "soft-zoom", "slide-left", "blur-in", "bounce-in", "flip-in", "float", "none"]), "animationDuration": number(0, 3000), "transitionPreset": string(20, ["none", "soft", "overlap", "sweep"]), "transitionDuration": number(200, 2000)}, ["pageId"]), obj({"updatedPageIds": IDS})),
        ToolDefinition("invitation.configure_opening", "Configure the invitation opening experience with bounded visual and accessibility options.", medium, edit, obj({"enabled": {"type":"boolean"}, "sceneId": string(80, ["soft-monogram", "royal-khmer-gate", "silk-curtain", "floral-reveal", "cinematic-photo", "minimal-editorial"]), "monogram": string(8), "subtitle": string(120), "subtitleKm": string(120), "enterText": string(40), "enterTextKm": string(60), "backgroundColor": COLOR, "backgroundAssetId": ID, "clearBackgroundImage": {"type":"boolean"}, "textVariant": string(20, ["dark", "light"]), "duration": number(0, 2500), "decorative": {"type":"boolean"}, "skipAllowed": {"type":"boolean"}}, []), obj({"updated": string(30)})),
        ToolDefinition("event.update_fields", "Update bounded English or Khmer event fields.", medium, edit, obj({"fields": obj({}, additional=True)}, ["fields"]), obj({"updatedFields": arr(string(80), 50)})),
        ToolDefinition("event.configure_details", "Configure invitation language, date presentation, Khmer date text, primary map link, and structured venue entries.", medium, edit, obj({
            "languageMode": string(10, ["en", "km", "both"]),
            "dateFormat": string(20, ["gregorian", "khmer", "both"]),
            "khmerDate": string(300),
            "mapUrl": string(2000),
            "venues": arr(obj({
                "name": string(300),
                "address": string(1000),
                "nameKm": string(300),
                "addressKm": string(1000),
                "mapUrl": string(2000),
            }), 50),
        }), obj({"updatedFields": arr(string(80), 20)})),
        ToolDefinition("event.update_schedule", "Replace the structured schedule.", medium, edit, obj({"schedule": arr(obj({}, additional=True), 100)}, ["schedule"]), obj({"updated": string(30)})),
        ToolDefinition("guest.create", "Create one invitation guest with bounded contact and grouping fields.", medium, manage, obj({"name": string(120), "phone": string(40), "email": string(254), "groupName": string(80), "householdId": string(80), "tags": arr(string(50), 20), "tableName": string(80), "seatLabel": string(40)}, ["name"]), obj({"guestId": ID}), confirmation=True),
        ToolDefinition("guest.update", "Update an existing invitation guest by stable guest ID.", medium, manage, obj({"guestId": ID, "name": string(120), "phone": string(40), "email": string(254), "groupName": string(80), "householdId": string(80), "tags": arr(string(50), 20), "tableName": string(80), "seatLabel": string(40)}, ["guestId", "name"]), obj({"updated": {"type": "boolean"}}), confirmation=True),
        ToolDefinition("guest.delete", "Permanently delete one invitation guest.", high, manage, obj({"guestId": ID}, ["guestId"]), obj({"deleted": {"type": "boolean"}}), reversible=False, confirmation=True),
        ToolDefinition("guest.check_in", "Set the check-in state for one invitation guest.", medium, manage, obj({"guestId": ID, "checkedIn": {"type": "boolean"}}, ["guestId", "checkedIn"]), obj({"checkedIn": {"type": "boolean"}}), confirmation=True),
        ToolDefinition("rsvp.update", "Update a stored RSVP status and guest count.", medium, manage, obj({"rsvpId": ID, "status": string(40, ["Yes, joyfully", "Unable to attend", "Maybe"]), "guestCount": number(1, 10)}, ["rsvpId", "status", "guestCount"]), obj({"updated": {"type": "boolean"}}), confirmation=True),
        ToolDefinition("analytics.read_summary", "Read authorized invitation analytics and response totals.", low, read, obj({}), obj({"analytics": obj({}, additional=True)})),
        ToolDefinition("account.read_usage", "Read the current account plan and bounded usage totals.", low, read, obj({}), obj({"usage": obj({}, additional=True)})),
        ToolDefinition("materials.list_folders", "Read the authorized invitation material folder hierarchy.", low, read, obj({}), obj({"folders": arr(obj({}, additional=True), 1000)}), executor="server"),
        ToolDefinition("materials.create_folder", "Create a project-local material folder under an authorized parent.", low, edit, obj({"folderName": string(120), "parentFolderId": ID}, ["folderName"]), obj({"folder": obj({}, additional=True)}), executor="server"),
        ToolDefinition("materials.import_folder", "Import a user-attached folder batch while preserving relative folder structure.", medium, edit, obj({"attachmentId": ID, "folderName": string(120)}, ["attachmentId"]), obj({"importJob": obj({}, additional=True)}), confirmation=True),
        ToolDefinition("materials.import_zip", "Import a user-attached ZIP materials archive using safe server extraction.", medium, edit, obj({"attachmentId": ID, "folderName": string(120)}, ["attachmentId"]), obj({"importJob": obj({}, additional=True)}), confirmation=True),
        ToolDefinition("materials.move", "Move an authorized material into a project-local folder.", low, edit, obj({"assetId": ID, "folderId": ID}, ["assetId", "folderId"]), obj({"asset": obj({}, additional=True)}), executor="server"),
        ToolDefinition("materials.rename", "Rename an authorized material without changing its stored object.", low, edit, obj({"assetId": ID, "name": string(180)}, ["assetId", "name"]), obj({"asset": obj({}, additional=True)}), executor="server"),
        ToolDefinition("materials.update_metadata", "Rename or organize an authorized invitation material.", medium, edit, obj({"assetId": ID, "name": string(180), "folder": string(240), "tags": arr(string(60), 30), "favorite": {"type": "boolean"}}, ["assetId", "name"]), obj({"asset": obj({}, additional=True)}), confirmation=True),
        ToolDefinition("materials.classify", "Apply bounded material classification and tags to authorized assets.", low, edit, obj({"assetIds": IDS, "category": string(60), "tags": arr(string(60), 30)}, ["assetIds", "category"]), obj({"updatedIds": IDS}), executor="server"),
        ToolDefinition("materials.find_duplicates", "Find duplicate authorized materials by checksum without deleting them.", low, read, obj({}), obj({"groups": arr(obj({}, additional=True), 500)}), executor="server"),
        ToolDefinition("materials.insert_into_page", "Insert an authorized material into an invitation page.", medium, edit, obj({"pageId": ID, "assetId": ID, "alt": string(1000)}, ["pageId", "assetId", "alt"]), obj({"createdIds": IDS})),
        ToolDefinition("design.analyze_reference", "Analyze authorized reference images into a schema-validated design blueprint; no executable markup is accepted.", low, edit, obj({"assetIds": IDS, "targetPageId": ID, "mode": string(30, ["create", "style", "palette", "typography"])}, ["assetIds", "mode"]), obj({"blueprint": obj({}, additional=True)}), executor="server"),
        ToolDefinition("design.apply_blueprint", "Apply a stored validated design blueprint through registered editor operations, or create a new invitation project when mode is create.", medium, edit, obj({"blueprintId": ID, "targetPageId": ID, "mode": string(30, ["create", "style", "palette", "typography"]), "previewOnly": {"type": "boolean"}, "newInvitationTitle": string(180), "slug": string(120)}, ["blueprintId", "mode"]), obj({"updatedIds": IDS, "createdPageIds": IDS, "createdInvitationId": ID, "slug": string(120), "previewOnly": {"type":"boolean"}})),
        ToolDefinition("invitation.archive", "Archive or restore the current invitation.", high, manage, obj({"archived": {"type": "boolean"}}, ["archived"]), obj({"archived": {"type": "boolean"}}), confirmation=True),
        ToolDefinition("invitation.update_operations", "Configure publication scheduling, expiration, or a custom domain.", high, manage, obj({"customDomain": string(253), "publishAt": number(0, 9e15), "unpublishAt": number(0, 9e15), "expiresAt": number(0, 9e15)}, []), obj({"operations": obj({}, additional=True)}), confirmation=True),
        ToolDefinition("invitation.configure_rsvp", "Enable or disable RSVP using the invitation's existing RSVP configuration.", medium, manage, obj({"enabled": {"type": "boolean"}}, ["enabled"]), obj({"enabled": {"type": "boolean"}}), confirmation=True, executor="server"),
        ToolDefinition("guest.read_delivery_status", "Read bounded guest delivery status only for a guest-operations task.", low, manage, obj({"guestIds": IDS}, []), obj({"delivery": arr(obj({}, additional=True), 500)}), executor="server"),
        ToolDefinition("asset.search", "Search authorized project and studio assets.", low, read, obj({"query": string(200), "types": arr(string(30), 10)}, ["query"]), obj({"assets": arr(obj({}, additional=True), 50)}), executor="server"),
        ToolDefinition("asset.insert", "Insert an authorized asset into a page.", medium, edit, obj({"pageId": ID, "assetId": ID, "alt": string(1000)}, ["pageId", "assetId", "alt"]), obj({"createdIds": IDS})),
        ToolDefinition("check.design", "Run the existing design checks.", low, read, obj({}), obj({"diagnostics": arr(obj({}, additional=True), 200)})),
        ToolDefinition("check.accessibility", "Run accessibility diagnostics.", low, read, obj({}), obj({"diagnostics": arr(obj({}, additional=True), 200)})),
        ToolDefinition("check.layout", "Run responsive layout diagnostics.", low, read, obj({"widths": arr(number(240, 1920), 20)}, []), obj({"diagnostics": arr(obj({}, additional=True), 500)})),
        ToolDefinition("check.print", "Run print-readiness diagnostics.", low, read, obj({}), obj({"diagnostics": arr(obj({}, additional=True), 200)})),
        ToolDefinition("fix.apply", "Apply one of the bounded fixes proposed by a prior check.", medium, edit, obj({"fixId": ID, "targets": IDS}, ["fixId"]), obj({"updatedIds": IDS})),
        ToolDefinition("preview.prepare", "Prepare a side-effect-free invitation preview.", low, read, obj({"mode": string(20, ["mobile", "tablet", "desktop", "print"])}, ["mode"]), obj({"preview": obj({}, additional=True)})),
        ToolDefinition("export.prepare", "Prepare an export without publishing.", medium, edit, obj({"format": string(20, ["png", "svg", "pdf", "backup"])}, ["format"]), obj({"prepared": string(30)}), confirmation=True),
        ToolDefinition("publish.prepare", "Prepare a publish or unpublish action for explicit confirmation.", high, manage, obj({"action": string(20, ["publish", "unpublish"])}, ["action"]), obj({"prepared": string(30)}), reversible=False, confirmation=True, executor="server"),
        ToolDefinition("message.prepare_send", "Prepare an external guest message; never send without confirmation.", high, manage, obj({"channel": string(20, ["email", "sms", "telegram", "whatsapp"]), "recipientIds": IDS, "message": TEXT}, ["channel", "recipientIds", "message"]), obj({"prepared": string(30)}), reversible=False, confirmation=True, executor="server"),
        ToolDefinition("editor.apply_workspace", "Apply a saved editor workspace mode without changing invitation content.", low, edit, obj({"mode": string(30, ["quick", "studio", "vector", "photo", "animation", "review", "operations"]), "profileId": ID}, ["mode"]), obj({"applied": string(30)})),
        ToolDefinition("marketplace.install_template", "Install an authorized marketplace template package for the workspace.", medium, manage, obj({"templateId": ID, "externalLicenseReference": string(200)}, ["templateId"]), obj({"installationId": ID}), confirmation=True),
        ToolDefinition("enterprise.prepare_protocol", "Prepare an enterprise or government ceremony protocol.", medium, manage, obj({"name": string(160), "classification": string(40, ["public", "internal", "restricted", "confidential"]), "protocolType": string(80), "document": obj({}, additional=True)}, ["name", "classification"]), obj({"protocolId": ID}), confirmation=True),
        ToolDefinition("animation.update_timeline", "Create or update a bounded object-animation timeline.", medium, edit, obj({"pageId": ID, "name": string(160), "timeline": obj({}, additional=True), "reducedMotion": obj({}, additional=True)}, ["pageId", "name", "timeline"]), obj({"projectId": ID})),
        ToolDefinition("publishing.configure_environment", "Prepare a named publication environment or schedule.", high, manage, obj({"name": string(80), "environmentType": string(30, ["preview", "staging", "production", "archive"]), "schedule": obj({}, additional=True), "access": obj({}, additional=True)}, ["name", "environmentType"]), obj({"environmentId": ID}), reversible=False, confirmation=True),
        ToolDefinition("merge.prepare_job", "Prepare a bounded data-merge job from an existing source.", high, manage, obj({"sourceId": ID, "mode": string(30, ["preview", "generate-drafts", "prepare-publications", "prepare-delivery"]), "rows": arr(obj({}, additional=True), 5000), "configuration": obj({}, additional=True)}, ["sourceId", "mode", "rows"]), obj({"jobId": ID}), reversible=False, confirmation=True),
        ToolDefinition("plugin.configure", "Install a declarative plugin version with exact declared grants.", high, manage, obj({"pluginKey": ID, "version": string(40), "permissions": arr(string(80), 20), "scope": obj({}, additional=True)}, ["pluginKey", "version", "permissions"]), obj({"installationId": ID}), reversible=False, confirmation=True),
        ToolDefinition("event.create_task", "Create an invitation-scoped operational event task.", low, edit, obj({"title": string(240), "category": string(80), "priority": string(30, ["low", "normal", "high", "critical"]), "dueAt": number(0, 9e15), "details": obj({}, additional=True)}, ["title"]), obj({"taskId": ID})),
        ToolDefinition("event.run_intelligence", "Run deterministic event-readiness and conflict analysis.", low, read, obj({}), obj({"findings": arr(obj({}, additional=True), 500)}), executor="server"),
        ToolDefinition("event.prepare_automation", "Prepare a bounded event automation using registered action types.", high, manage, obj({"name": string(160), "triggerType": string(80), "trigger": obj({}, additional=True), "conditions": arr(obj({}, additional=True), 100), "actions": arr(obj({}, additional=True), 40)}, ["name", "triggerType", "actions"]), obj({"automationId": ID}), reversible=False, confirmation=True),
    ]


TOOLS = {item.id: item for item in _defs()}


def tool_catalog() -> list[dict[str, Any]]:
    return [TOOLS[key].public() for key in sorted(TOOLS)]


def get_tool(tool_id: str) -> ToolDefinition:
    try:
        return TOOLS[str(tool_id)]
    except KeyError as exc:
        raise ToolValidationError(f"Unknown tool: {tool_id}", "unknown_tool") from exc


def _reject_forbidden(value: Any, key: str = "") -> None:
    if key in FORBIDDEN_KEYS:
        raise ToolValidationError(f"Forbidden tool argument key: {key}", "forbidden_argument")
    if isinstance(value, dict):
        for child_key, child in value.items():
            _reject_forbidden(child, str(child_key))
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden(child, key)
    elif isinstance(value, str):
        for pattern in FORBIDDEN_VALUE_PATTERNS:
            if pattern.search(value):
                raise ToolValidationError("Tool arguments contain a forbidden executable or destination pattern.", "forbidden_argument")


def _validate(schema: dict[str, Any], value: Any, path: str = "arguments") -> Any:
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            raise ToolValidationError(f"{path} must be an object")
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                raise ToolValidationError(f"{path}.{name} is required")
        if not schema.get("additionalProperties", False):
            unknown = sorted(set(value) - set(properties))
            if unknown:
                raise ToolValidationError(f"Unknown {path} fields: {', '.join(unknown)}")
        result = {}
        for name, child in value.items():
            result[name] = _validate(properties.get(name, {}), child, f"{path}.{name}") if name in properties else copy.deepcopy(child)
        return result
    if kind == "array":
        if not isinstance(value, list):
            raise ToolValidationError(f"{path} must be an array")
        if len(value) > int(schema.get("maxItems", 100)):
            raise ToolValidationError(f"{path} contains too many items")
        return [_validate(schema.get("items", {}), item, f"{path}[{index}]") for index, item in enumerate(value)]
    if kind == "string":
        if not isinstance(value, str):
            raise ToolValidationError(f"{path} must be a string")
        if len(value) > int(schema.get("maxLength", 50_000)):
            raise ToolValidationError(f"{path} is too long")
        if "enum" in schema and value not in schema["enum"]:
            raise ToolValidationError(f"{path} has an unsupported value")
        fmt = schema.get("format")
        if fmt == "stable-id" and not ID_RE.fullmatch(value):
            raise ToolValidationError(f"{path} is not a valid stable ID")
        if fmt == "hex-color" and not HEX_RE.fullmatch(value):
            raise ToolValidationError(f"{path} is not a valid color")
        if fmt == "geometry" and not GEOMETRY_RE.fullmatch(value):
            raise ToolValidationError(f"{path} is not valid document geometry")
        return value
    if kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ToolValidationError(f"{path} must be a number")
        number_value = float(value)
        if number_value < float(schema.get("minimum", -1e9)) or number_value > float(schema.get("maximum", 1e9)):
            raise ToolValidationError(f"{path} is outside the allowed range")
        return value
    if kind == "boolean":
        if not isinstance(value, bool):
            raise ToolValidationError(f"{path} must be boolean")
        return value
    return copy.deepcopy(value)


def validate_tool_call(call: Any) -> dict[str, Any]:
    if not isinstance(call, dict):
        raise ToolValidationError("Tool call must be an object")
    allowed = {"id", "arguments", "reason", "clientCallId"}
    unknown = sorted(set(call) - allowed)
    if unknown:
        raise ToolValidationError(f"Unknown tool-call fields: {', '.join(unknown)}")
    tool = get_tool(str(call.get("id", "")))
    arguments = call.get("arguments", {})
    _reject_forbidden(arguments)
    validated = _validate(tool.input_schema, arguments)
    encoded = json.dumps(validated, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > 200_000:
        raise ToolValidationError("Tool arguments exceed the bounded size")
    return {
        "id": tool.id,
        "arguments": validated,
        "reason": str(call.get("reason", ""))[:1000],
        "clientCallId": str(call.get("clientCallId", ""))[:120],
        "risk": tool.risk,
        "permission": tool.permission,
        "reversible": tool.reversible,
        "confirmationRequired": tool.confirmation,
        "executor": tool.executor,
    }


def validate_tool_calls(calls: Any, maximum: int = 40) -> list[dict[str, Any]]:
    if not isinstance(calls, list):
        raise ToolValidationError("toolCalls must be an array")
    if len(calls) > maximum:
        raise ToolValidationError("The provider requested too many tool calls", "too_many_tool_calls")
    return [validate_tool_call(call) for call in calls]

"""Cumulative V29-V32 invitation-document normalization.

This module is intentionally dependency free and preserves unknown fields while
validating the new professional scene, raster, collaboration, and platform
metadata boundaries. It complements the browser migration in
``document-schema-v32.js`` and is used at every server persistence boundary.
"""
from __future__ import annotations

import copy
import math
import re
import uuid
from typing import Any

CURRENT_VERSION = 27
MAX_SCENE_NODES = 10_000
MAX_SCENE_DEPTH = 24
MAX_RASTER_DOCUMENTS = 128
MAX_RASTER_OPERATIONS = 2_000
MAX_RASTER_LAYERS = 256
MAX_VECTOR_PATH_BYTES = 1_000_000
_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,180}$")
_ALLOWED_NODE_TYPES = {
    "object", "text", "image", "shape", "decoration", "group", "frame",
    "vector", "component-definition", "component-instance", "raster",
}
_ALLOWED_BLEND_MODES = {
    "normal", "multiply", "screen", "overlay", "darken", "lighten",
    "color-dodge", "color-burn", "hard-light", "soft-light", "difference",
    "exclusion", "hue", "saturation", "color", "luminosity",
}
_ALLOWED_RASTER_STATUS = {"draft", "rendering", "ready", "failed", "stale"}


def _finite(value: Any, fallback: float = 0.0, minimum: float = -1e9, maximum: float = 1e9) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    if not math.isfinite(number):
        number = fallback
    return max(minimum, min(maximum, number))


def _text(value: Any, maximum: int = 180) -> str:
    return "".join(ch for ch in str(value or "") if ord(ch) >= 32 and ord(ch) != 127)[:maximum]


def _id(value: Any, prefix: str = "id") -> str:
    candidate = _text(value, 180)
    if candidate and _ID_RE.fullmatch(candidate):
        return candidate
    return f"{prefix}-{uuid.uuid4()}"


def _matrix(value: Any) -> list[float]:
    defaults = [1, 0, 0, 1, 0, 0]
    if not isinstance(value, list) or len(value) < 6:
        return defaults
    return [_finite(value[index], defaults[index], -1_000_000, 1_000_000) for index in range(6)]


def _normalize_vector(vector: Any, strict: bool) -> dict[str, Any]:
    source = copy.deepcopy(vector) if isinstance(vector, dict) else {}
    kind = _text(source.get("kind") or "path", 40)
    allowed = {"rectangle", "rounded-rectangle", "ellipse", "circle", "line", "arrow", "polygon", "star", "heart", "path", "svg-import"}
    if strict and kind not in allowed:
        raise ValueError("Unsupported professional vector kind")
    source["kind"] = kind if kind in allowed else "path"
    source["viewBox"] = source.get("viewBox") if isinstance(source.get("viewBox"), dict) else {"x": 0, "y": 0, "width": 100, "height": 100}
    for key in ("x", "y", "width", "height"):
        source["viewBox"][key] = _finite(source["viewBox"].get(key), 100 if key in {"width", "height"} else 0, -1_000_000, 1_000_000)
    source["fill"] = source.get("fill") if isinstance(source.get("fill"), dict) else {"type": "solid", "color": "#d6ad60"}
    source["stroke"] = source.get("stroke") if isinstance(source.get("stroke"), dict) else {"color": "#000000", "width": 0, "cap": "round", "join": "round", "dash": []}
    source["stroke"]["width"] = _finite(source["stroke"].get("width"), 0, 0, 1_000)
    source["opacity"] = _finite(source.get("opacity"), 1, 0, 1)
    source["fillRule"] = "evenodd" if source.get("fillRule") == "evenodd" else "nonzero"
    raw_path = str(source.get("pathData") or "")
    if len(raw_path.encode("utf-8")) > MAX_VECTOR_PATH_BYTES:
        raise ValueError("Vector path data exceeds the supported size")
    paths = source.get("paths") if isinstance(source.get("paths"), list) else []
    source["paths"] = paths[:2_000]
    imported = str(source.get("sanitizedSvg") or "")
    if imported and len(imported.encode("utf-8")) > MAX_VECTOR_PATH_BYTES:
        raise ValueError("Imported SVG exceeds the supported size")
    # The browser sanitizer is the authoritative SVG parser. The server still
    # rejects executable constructs if a malicious client bypasses it.
    lowered = imported.lower()
    forbidden = ("<script", "<foreignobject", "javascript:", "data:text/html", " onload=", " onclick=", " onerror=")
    if imported and any(token in lowered for token in forbidden):
        raise ValueError("Imported SVG contains executable or external content")
    return source


def _normalize_scene(document: dict[str, Any], strict: bool) -> dict[str, Any]:
    scene = copy.deepcopy(document.get("professionalScene")) if isinstance(document.get("professionalScene"), dict) else {"version": 1, "nodes": {}, "roots": {}, "components": {}, "guides": {}, "grid": {}}
    nodes = scene.get("nodes") if isinstance(scene.get("nodes"), dict) else {}
    if len(nodes) > MAX_SCENE_NODES:
        raise ValueError("Professional scene exceeds the 10,000-layer limit")
    normalized: dict[str, dict[str, Any]] = {}
    for raw_id, raw_node in nodes.items():
        if not isinstance(raw_node, dict):
            if strict:
                raise ValueError("Professional scene node must be an object")
            continue
        node_id = _id(raw_id, "layer")
        node = copy.deepcopy(raw_node)
        node["id"] = node_id
        node["layerId"] = _id(node.get("layerId") or node_id, "layer")
        node["objectId"] = _text(node.get("objectId"), 180)
        node["canvasId"] = _text(node.get("canvasId") or "hero", 180)
        node["parentId"] = _text(node.get("parentId"), 180)
        node_type = _text(node.get("type") or "object", 40)
        if strict and node_type not in _ALLOWED_NODE_TYPES:
            raise ValueError("Unsupported professional scene node type")
        node["type"] = node_type if node_type in _ALLOWED_NODE_TYPES else "object"
        node["name"] = _text(node.get("name") or "Layer", 180)
        node["orderKey"] = _text(node.get("orderKey") or "000000000001", 100)
        node["visible"] = node.get("visible") is not False
        node["locked"] = node.get("locked") is True
        node["opacity"] = _finite(node.get("opacity"), 1, 0, 1)
        blend = _text(node.get("blendMode") or "normal", 40)
        node["blendMode"] = blend if blend in _ALLOWED_BLEND_MODES else "normal"
        node["tags"] = [_text(item, 48) for item in (node.get("tags") if isinstance(node.get("tags"), list) else [])[:32]]
        node["metadata"] = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        node["role"] = _text(node.get("role"), 100)
        node["constraints"] = node.get("constraints") if isinstance(node.get("constraints"), dict) else {}
        transform = node.get("transform") if isinstance(node.get("transform"), dict) else {}
        node["transform"] = {
            **transform,
            "matrix": _matrix(transform.get("matrix")),
            "origin": transform.get("origin") if isinstance(transform.get("origin"), dict) else {"x": 0.5, "y": 0.5},
        }
        if node["type"] == "vector":
            data = node.get("data") if isinstance(node.get("data"), dict) else {}
            data["vector"] = _normalize_vector(data.get("vector"), strict)
            node["data"] = data
        else:
            node["data"] = node.get("data") if isinstance(node.get("data"), dict) else {}
        children = node.get("children") if isinstance(node.get("children"), list) else []
        node["children"] = list(dict.fromkeys(_text(child, 180) for child in children if str(child) != node_id))[:MAX_SCENE_NODES]
        normalized[node_id] = node
    for node in normalized.values():
        node["children"] = [child for child in node["children"] if child in normalized]
        if node["parentId"] and node["parentId"] not in normalized:
            node["parentId"] = ""
    # Reject cycles and excessive depth without relying on DOM order.
    def depth(node_id: str, trail: set[str]) -> int:
        if node_id in trail:
            raise ValueError("Professional scene contains a hierarchy cycle")
        parent = normalized[node_id].get("parentId")
        if not parent:
            return 1
        return 1 + depth(parent, {*trail, node_id})
    for node_id in normalized:
        if depth(node_id, set()) > MAX_SCENE_DEPTH:
            raise ValueError("Professional scene nesting exceeds 24 levels")
    roots_source = scene.get("roots") if isinstance(scene.get("roots"), dict) else {}
    roots: dict[str, list[str]] = {}
    for canvas, values in roots_source.items():
        roots[_text(canvas, 180)] = [item for item in dict.fromkeys(_text(value, 180) for value in (values if isinstance(values, list) else [])) if item in normalized and not normalized[item]["parentId"]]
    for node_id, node in normalized.items():
        if not node["parentId"]:
            roots.setdefault(node["canvasId"], [])
            if node_id not in roots[node["canvasId"]]:
                roots[node["canvasId"]].append(node_id)
    scene["version"] = 1
    scene["nodes"] = normalized
    scene["roots"] = roots
    scene["components"] = scene.get("components") if isinstance(scene.get("components"), dict) else {}
    scene["guides"] = scene.get("guides") if isinstance(scene.get("guides"), dict) else {}
    scene["grid"] = scene.get("grid") if isinstance(scene.get("grid"), dict) else {"enabled": False, "size": 8, "subdivisions": 1, "snapStrength": 8}
    scene["units"] = _text(scene.get("units") or "px", 12)
    return scene


def _normalize_raster(document: dict[str, Any]) -> dict[str, Any]:
    source = document.get("rasterEdits") if isinstance(document.get("rasterEdits"), dict) else {}
    if len(source) > MAX_RASTER_DOCUMENTS:
        raise ValueError("Invitation references too many raster edit documents")
    output: dict[str, dict[str, Any]] = {}
    for raw_id, raw in source.items():
        if not isinstance(raw, dict):
            continue
        item = copy.deepcopy(raw)
        edit_id = _id(item.get("id") or raw_id, "raster")
        item["id"] = edit_id
        item["version"] = 1
        item["sourceAssetId"] = _text(item.get("sourceAssetId"), 180)
        item["sourceAssetVersion"] = max(1, int(_finite(item.get("sourceAssetVersion"), 1, 1, 1e9)))
        item["width"] = max(0, int(_finite(item.get("width"), 0, 0, 50_000)))
        item["height"] = max(0, int(_finite(item.get("height"), 0, 0, 50_000)))
        item["mime"] = _text(item.get("mime") or "image/png", 100)
        item["operations"] = (item.get("operations") if isinstance(item.get("operations"), list) else [])[:MAX_RASTER_OPERATIONS]
        item["adjustments"] = (item.get("adjustments") if isinstance(item.get("adjustments"), list) else [])[:256]
        item["layers"] = (item.get("layers") if isinstance(item.get("layers"), list) else [])[:MAX_RASTER_LAYERS]
        item["masks"] = item.get("masks") if isinstance(item.get("masks"), dict) else {}
        item["previewAssetId"] = _text(item.get("previewAssetId"), 180)
        item["exportAssetId"] = _text(item.get("exportAssetId"), 180)
        status = _text(item.get("status") or "draft", 30)
        item["status"] = status if status in _ALLOWED_RASTER_STATUS else "draft"
        item["fingerprint"] = _text(item.get("fingerprint"), 180)
        output[edit_id] = item
    return output


def _bounded_list(value: Any, maximum: int) -> list[Any]:
    return copy.deepcopy(value[:maximum]) if isinstance(value, list) else []


def _normalize_future(document: dict[str, Any]) -> None:
    editor = document.get("editorExperienceV34") if isinstance(document.get("editorExperienceV34"), dict) else {}
    document["editorExperienceV34"] = {
        **editor,
        "version": 1,
        "mode": _text(editor.get("mode") or "quick", 30),
        "workspaceProfileId": _text(editor.get("workspaceProfileId"), 180),
        "advancedPanels": _bounded_list(editor.get("advancedPanels"), 64),
    }
    agent = document.get("aiAgentV35") if isinstance(document.get("aiAgentV35"), dict) else {}
    document["aiAgentV35"] = {
        **agent,
        "version": 1,
        "routingPolicyId": _text(agent.get("routingPolicyId"), 180),
        "workflowIds": [_text(x, 180) for x in _bounded_list(agent.get("workflowIds"), 100)],
        "brandContext": agent.get("brandContext") if isinstance(agent.get("brandContext"), dict) else {},
    }
    marketplace = document.get("marketplaceV36") if isinstance(document.get("marketplaceV36"), dict) else {}
    document["marketplaceV36"] = {
        **marketplace,
        "version": 1,
        "templateId": _text(marketplace.get("templateId"), 180),
        "templateVersion": max(0, int(_finite(marketplace.get("templateVersion"), 0, 0, 1e9))),
        "detached": marketplace.get("detached") is True,
        "licenseReference": _text(marketplace.get("licenseReference"), 240),
    }
    enterprise = document.get("enterpriseV42") if isinstance(document.get("enterpriseV42"), dict) else {}
    classification = _text(enterprise.get("classification") or "internal", 40)
    document["enterpriseV42"] = {
        **enterprise,
        "version": 1,
        "protocolId": _text(enterprise.get("protocolId"), 180),
        "classification": classification if classification in {"public", "internal", "restricted", "confidential"} else "internal",
        "approvalPolicyId": _text(enterprise.get("approvalPolicyId"), 180),
        "officialNumber": _text(enterprise.get("officialNumber"), 120),
        "protocolOrder": _bounded_list(enterprise.get("protocolOrder"), 1000),
    }
    animation = document.get("animationV44") if isinstance(document.get("animationV44"), dict) else {}
    document["animationV44"] = {
        **animation,
        "version": 1,
        "activeProjectId": _text(animation.get("activeProjectId"), 180),
        "fallbackTimeline": animation.get("fallbackTimeline") if isinstance(animation.get("fallbackTimeline"), dict) else {"version": 1, "duration": 0, "tracks": []},
        "reducedMotion": animation.get("reducedMotion") if isinstance(animation.get("reducedMotion"), dict) else {"mode": "simplify"},
    }
    publishing = document.get("publishingV45") if isinstance(document.get("publishingV45"), dict) else {}
    document["publishingV45"] = {
        **publishing,
        "version": 1,
        "activeEnvironment": _text(publishing.get("activeEnvironment") or "production", 80),
        "canonicalDomainId": _text(publishing.get("canonicalDomainId"), 180),
        "indexing": publishing.get("indexing") is True,
        "expiryAt": max(0, int(_finite(publishing.get("expiryAt"), 0, 0, 9e15))),
        "archiveBehavior": _text(publishing.get("archiveBehavior") or "show-archived", 40),
    }
    merge = document.get("dataMergeV47") if isinstance(document.get("dataMergeV47"), dict) else {}
    document["dataMergeV47"] = {
        **merge,
        "version": 1,
        "sourceId": _text(merge.get("sourceId"), 180),
        "mergeFields": _bounded_list(merge.get("mergeFields"), 500),
        "variantPolicy": merge.get("variantPolicy") if isinstance(merge.get("variantPolicy"), dict) else {},
    }
    plugins = document.get("pluginsV48") if isinstance(document.get("pluginsV48"), dict) else {}
    document["pluginsV48"] = {
        **plugins,
        "version": 1,
        "blocks": _bounded_list(plugins.get("blocks"), 200),
        "configurations": plugins.get("configurations") if isinstance(plugins.get("configurations"), dict) else {},
    }
    event = document.get("eventEcosystemV52") if isinstance(document.get("eventEcosystemV52"), dict) else {}
    document["eventEcosystemV52"] = {
        **event,
        "version": 1,
        "programIds": [_text(x, 180) for x in _bounded_list(event.get("programIds"), 500)],
        "primaryProgramId": _text(event.get("primaryProgramId"), 180),
        "timezone": _text(event.get("timezone") or "Asia/Phnom_Penh", 80),
        "automationIds": [_text(x, 180) for x in _bounded_list(event.get("automationIds"), 200)],
        "operationsMode": _text(event.get("operationsMode") or "standard", 40),
    }


def normalize_document_v32(document: dict[str, Any], *, strict: bool = True, mutate: bool = True) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ValueError("Invitation document must be an object")
    output = document if mutate else copy.deepcopy(document)
    previous = max(0, int(_finite(output.get("schemaVersion"), 14, 0, CURRENT_VERSION)))
    features = output.get("featureFlags") if isinstance(output.get("featureFlags"), dict) else {}
    output["featureFlags"] = {
        **features,
        "professionalLayers": features.get("professionalLayers") is not False,
        "vectorEditing": features.get("vectorEditing") is not False,
        "rasterWorkspace": features.get("rasterWorkspace") is not False,
        "collaborationV31": features.get("collaborationV31") is not False,
        "productionV32": features.get("productionV32") is not False,
        "unifiedEditorV34": features.get("unifiedEditorV34") is not False,
        "productionAgentV35": features.get("productionAgentV35") is not False,
        "templateMarketplaceV36": features.get("templateMarketplaceV36") is not False,
        "enterpriseGovernmentV42": features.get("enterpriseGovernmentV42") is not False,
        "advancedAnimationV44": features.get("advancedAnimationV44") is not False,
        "publishingDomainsV45": features.get("publishingDomainsV45") is not False,
        "dataMergeV47": features.get("dataMergeV47") is not False,
        "pluginPlatformV48": features.get("pluginPlatformV48") is not False,
        "eventEcosystemV52": features.get("eventEcosystemV52") is not False,
    }
    output["professionalScene"] = _normalize_scene(output, strict)
    output["rasterEdits"] = _normalize_raster(output)
    collaboration = output.get("collaborationDocument") if isinstance(output.get("collaborationDocument"), dict) else {}
    output["collaborationDocument"] = {
        **collaboration,
        "version": 1,
        "documentId": _id(collaboration.get("documentId") or output.get("id") or output.get("invitationId"), "doc"),
        "epoch": max(1, int(_finite(collaboration.get("epoch"), 1, 1, 1e9))),
        "checkpointId": _text(collaboration.get("checkpointId"), 180),
        "checkpointFingerprint": _text(collaboration.get("checkpointFingerprint"), 180),
        "stateVector": collaboration.get("stateVector") if isinstance(collaboration.get("stateVector"), dict) else {},
        "actors": collaboration.get("actors") if isinstance(collaboration.get("actors"), dict) else {},
        "sequenceVersion": max(1, int(_finite(collaboration.get("sequenceVersion"), 1, 1, 1e9))),
        "migrationSource": _text(collaboration.get("migrationSource") or f"schema-{previous}", 80),
    }
    platform = output.get("platformMetadata") if isinstance(output.get("platformMetadata"), dict) else {}
    output["platformMetadata"] = {
        **platform,
        "version": 1,
        "workspaceHint": _text(platform.get("workspaceHint"), 180),
        "tenantMigration": "server-authoritative",
        "documentEpoch": max(1, int(_finite(platform.get("documentEpoch"), 1, 1, 1e9))),
        "lastMigratedFrom": max(0, int(_finite(platform.get("lastMigratedFrom"), previous, 0, CURRENT_VERSION))),
        "lastMigratedAt": 0,
    }
    _normalize_future(output)
    output["schemaVersion"] = max(CURRENT_VERSION, previous)
    return output

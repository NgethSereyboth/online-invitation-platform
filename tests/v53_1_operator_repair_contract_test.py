#!/usr/bin/env python3
"""Focused contracts for the V53.1 operator security/reliability repair."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import time
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai_agent.local_providers import _json_request
from ai_agent.service import AgentService, AgentServiceError


class _RedirectTarget(BaseHTTPRequestHandler):
    hits = 0

    def do_GET(self):
        type(self).hits += 1
        body = b'{"redirected":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class _RedirectSource(BaseHTTPRequestHandler):
    destination = ""

    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", type(self).destination)
        self.end_headers()

    def log_message(self, *_args):
        pass


def _serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_provider_redirects_are_not_followed():
    target = _serve(_RedirectTarget)
    source = _serve(_RedirectSource)
    _RedirectTarget.hits = 0
    _RedirectSource.destination = f"http://127.0.0.1:{target.server_port}/escaped"
    try:
        try:
            _json_request(f"http://127.0.0.1:{source.server_port}/models", 2)
            raise AssertionError("provider redirect was unexpectedly followed")
        except urllib.error.HTTPError as exc:
            assert exc.code == 302
        assert _RedirectTarget.hits == 0
    finally:
        source.shutdown()
        target.shutdown()
        source.server_close()
        target.server_close()


def test_authorization_is_single_use_and_endpoint_scoped():
    service = object.__new__(AgentService)
    service.audit = None
    service._lock = threading.Lock()
    service._tool_authorizations = {
        "valid": {
            "userId": "user-1", "invitationId": "invite-1", "planId": "plan-1",
            "index": 0, "toolId": "materials.create_folder", "expiresAt": time.time() + 30,
        },
        "wrong-route": {
            "userId": "user-1", "invitationId": "invite-1", "planId": "plan-1",
            "index": 0, "toolId": "materials.create_folder", "expiresAt": time.time() + 30,
        },
    }
    record = service.consume_tool_authorization(
        "valid", "invite-1", "user-1", "materials.create_folder", "POST",
        "/api/invitations/invite-1/materials/folders",
    )
    assert record["planId"] == "plan-1"
    try:
        service.consume_tool_authorization(
            "valid", "invite-1", "user-1", "materials.create_folder", "POST",
            "/api/invitations/invite-1/materials/folders",
        )
        raise AssertionError("authorization token was reusable")
    except AgentServiceError as exc:
        assert exc.code == "ai_tool_authorization_invalid"
    try:
        service.consume_tool_authorization(
            "wrong-route", "invite-1", "user-1", "materials.create_folder", "POST",
            "/api/invitations/invite-1/archive",
        )
        raise AssertionError("authorization token escaped its endpoint scope")
    except AgentServiceError as exc:
        assert exc.code == "ai_tool_authorization_scope_mismatch"


def test_browser_contracts_and_route_budget():
    agent = (ROOT / "ai-creative-agent-v28.js").read_text(encoding="utf-8")
    registry = (ROOT / "ai-agent-tool-registry-v28.js").read_text(encoding="utf-8")
    upload = (ROOT / "upload-folder-client-v53.js").read_text(encoding="utf-8")
    assert "sessionOffline" in agent and "agentServerAvailable" in agent
    assert "MULTIPLE_SERVER_MUTATIONS_UNSUPPORTED" in registry
    assert "X-EInvite-AI-Authorization" in registry
    assert "authorizationHeaders" in upload
    bundle_bytes = (ROOT / "bundle-index-v15.js").stat().st_size + (ROOT / "bundle-index-v15.css").stat().st_size
    assert bundle_bytes <= 1_420_000, bundle_bytes


if __name__ == "__main__":
    test_provider_redirects_are_not_followed()
    test_authorization_is_single_use_and_endpoint_scoped()
    test_browser_contracts_and_route_budget()
    print("V53_1_OPERATOR_REPAIR_CONTRACT_TEST_PASSED")

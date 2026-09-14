#!/usr/bin/env python3
"""Deterministic cross-tab routing checks for invitation-specific management URLs."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "invitation-context.js").read_text(encoding="utf-8")


def run_case(pathname: str, remembered: str, expected: str) -> dict:
    script = f"""
const vm = require('vm');
const source = {json.dumps(SOURCE)};
const store = new Map([['sovan-active-invite',{json.dumps(remembered)}]]);
const anchors = [
  {{href:'guests.html',getAttribute(k){{return k==='href'?this.href:null}},setAttribute(k,v){{if(k==='href')this.href=v}}}},
  {{href:'analytics.html',getAttribute(k){{return k==='href'?this.href:null}},setAttribute(k,v){{if(k==='href')this.href=v}}}}
];
const context = {{
  window: {{}},
  location: {{pathname:{json.dumps(pathname)},search:'',href:''}},
  URLSearchParams,
  encodeURIComponent,
  decodeURIComponent,
  localStorage: {{getItem:k=>store.has(k)?store.get(k):null,setItem:(k,v)=>store.set(k,String(v))}},
  document: {{readyState:'complete',querySelectorAll:()=>anchors,addEventListener:()=>{{}}}},
  Set,
  String
}};
context.window = context;
vm.createContext(context);
vm.runInContext(source, context);
console.log(JSON.stringify({{
  id: context.EInviteContext.getInvitationId(),
  explicitId: context.EInviteContext.explicitId,
  section: context.EInviteContext.section,
  remembered: store.get('sovan-active-invite'),
  guestHref: anchors[0].href,
  analyticsHref: anchors[1].href,
  editorRoute: context.EInviteContext.route(context.EInviteContext.getInvitationId(),'editor')
}}));
"""
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", check=True)
    data = json.loads(proc.stdout)
    assert data["id"] == expected, data
    assert data["explicitId"] == expected, data
    assert data["remembered"] == expected, data
    assert data["guestHref"] == f"/invitations/{expected}/guests", data
    assert data["analyticsHref"] == f"/invitations/{expected}/analytics", data
    assert data["editorRoute"] == f"/invitations/{expected}/editor", data
    return data


def main() -> int:
    first = run_case("/invitations/invite-a/editor", "invite-b", "invite-a")
    second = run_case("/invitations/invite-b/analytics", "invite-a", "invite-b")
    assert first["id"] != second["id"]
    assert first["section"] == "editor"
    assert second["section"] == "analytics"
    print("V12_ROUTING_CONTEXT_TEST_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

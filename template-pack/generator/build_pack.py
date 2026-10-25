# -*- coding: utf-8 -*-
"""Builds specs for all templates (and optional previews). Usage: PACK_FONTS=... python3 build_pack.py [--preview] [id ...]"""
import json, os, sys
from engine import T, CANVASES, FONTS, M, svg_aspect
import copybank, layouts, catalog
copybank.add_word_breaks()

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def build(tp):
    spec = dict(id=tp["id"], category=tp["cat"], canvas=dict(CANVASES[tp["canvas"]], key=tp["canvas"]), palette=tp["pal"],
                typography=tp["kind"], tags=tp["tags"], _copy=copybank.C, pages=[], notes=[])
    km = copybank.EVENT_KM[tp["ev"]] + " " + copybank.STYLE_KM[tp["style"]]
    spec["name"] = {"en": tp["en"], "km": km}
    for i, (b, o) in enumerate(tp["pages"]):
        t = T(tp["id"], tp["canvas"], tp["pal"], tp["kind"], copybank.C, ROOT)
        layouts.BUILDERS[b](t, o)
        spec["pages"].append(dict(name="Page %d" % (i + 1), builder=b, layers=t.layers))
        spec["notes"] += ["p%d: %s" % (i + 1, n) for n in t.notes]
        spec["photoSlots"] = sorted(set(spec.get("photoSlots", []) + t.photos))
    return spec

def write_all(only=None):
    if not M.ok: sys.exit("PACK_FONTS not set or Pillow lacks raqm: refusing to write estimated layouts")
    os.makedirs(os.path.join(ROOT, "templates"), exist_ok=True)
    cat = []
    for tp in catalog.TEMPLATES:
        sp = build(tp)
        sp.pop("_copy")
        json.dump(sp, open(os.path.join(ROOT, "templates", tp["id"] + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        cat.append(dict(id=tp["id"], category=tp["cat"], canvas=tp["canvas"], name=sp["name"], tags=tp["tags"], pages=len(sp["pages"]),
                        palette=tp["pal"], typography=tp["kind"], photoSlots=sp.get("photoSlots", [])))
    json.dump(dict(version=1, count=len(cat), templates=cat), open(os.path.join(ROOT, "catalog.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(dict(version=1, note="Khmer is Claude-drafted; native-speaker review required before launch. risk: low|med",
                   copy=copybank.C, calendar=copybank.CALENDAR), open(os.path.join(ROOT, "copy-bank.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    fj = {r: dict(family=f[0], licence=f[1], source="https://github.com/google/fonts/tree/main/ofl (find the directory for this family)") for r, f in FONTS.items()}
    json.dump(dict(version=1, note="Roles used by templates/*.json. Map to the app's font registry; add a lazily loaded self-hosted OFL woff2 only for a family the registry lacks (amendment TP-OD-1).", roles=fj),
              open(os.path.join(ROOT, "fonts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rows = ["# Khmer template copy map (Claude-drafted, native review required)", "",
            "Source of truth: `copy-bank.json`. Word breaks (U+200B) are stripped here for reading only. risk = how likely a native speaker would change it.", "",
            "| key | English | Khmer | risk |", "|---|---|---|---|"]
    for k, v in copybank.C.items():
        rows.append("| `%s` | %s | %s | %s |" % (k, v["en"], v["km"].replace("\u200b", ""), v["risk"]))
    open(os.path.join(ROOT, "KHMER-COPY-MAP.md"), "w", encoding="utf-8").write("\n".join(rows) + "\n")
    print("wrote %d templates" % len(cat))

if __name__ == "__main__":
    if "--write" in sys.argv: write_all(); sys.exit(0)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    prev = "--preview" in sys.argv
    out = os.path.join(ROOT, "_preview"); os.makedirs(out, exist_ok=True)
    from preview import render
    for tp in catalog.TEMPLATES:
        if args and tp["id"] not in args: continue
        sp = build(tp)
        print(tp["id"], "OK" if not sp["notes"] else sp["notes"])
        if prev:
            for i, pg in enumerate(sp["pages"]):
                render(sp, pg, ROOT, 600).save(os.path.join(out, "%s-%d.png" % (tp["id"], i + 1)))

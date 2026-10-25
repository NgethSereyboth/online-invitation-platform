# -*- coding: utf-8 -*-
"""Pack linter. Exit 1 on any ERROR. Usage: python3 lint.py (after build_pack has written templates/)."""
import json, os, re, sys, glob
from engine import contrast, lum

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KH = re.compile(r"[ក-៿]")
errs, warns = [], []

def under(pal, layers, i, L):
    """Fill colour(s) behind text layer i (opaque shapes covering its centre, else page bg)."""
    cx, cy = L["x"] + L["w"] / 2, L["y"] + L["h"] / 2
    fills = None
    for P in layers[:i]:
        f = P.get("fill")
        if P["type"] == "bg":
            fills = [f] if not isinstance(f, dict) else [s[0] for s in f["gradient"]["stops"]]
        elif P["type"] == "svg" and P["src"].endswith("ribbon-banner.svg") and P["x"] <= cx <= P["x"] + P["w"] and P["y"] <= cy <= P["y"] + P["h"]:
            fills = [P["color"]]
        elif P["type"] == "shape" and f and P.get("opacity", 1) >= .9 and P["x"] <= cx <= P["x"] + P["w"] and P["y"] <= cy <= P["y"] + P["h"]:
            fills = [f]
    return [pal.get(x, x) for x in fills or []]

def lint_template(tp, copy):
    pal, W = tp["palette"], tp["canvas"]["w"]
    for pi, pg in enumerate(tp["pages"]):
        ly = pg["layers"]
        for i, L in enumerate(ly):
            tag = "%s p%d %s" % (tp["id"], pi + 1, L["id"])
            if L["type"] == "text":
                if "copy" in L and L["copy"] not in copy: errs.append("%s: unknown copy key %s" % (tag, L["copy"]))
                if L.get("literal") and KH.search(L["literal"]): errs.append("%s: literal Khmer in layer" % tag)
                col = pal.get(L["color"], L["color"])
                big = L["size"] / (W / 1000) >= 36 or (L["weight"] >= 700 and L["size"] / (W / 1000) >= 28)
                need = 3.0 if big else 4.5
                for bgc in under(pal, ly, i, L):
                    cr = contrast(col, bgc)
                    if cr < need: errs.append("%s: contrast %.2f < %.1f (%s on %s)" % (tag, cr, need, L["color"], bgc))
                if L["size"] / W < 0.0215 and L["lang"] == "km": warns.append("%s: Khmer size %.1f%% of width" % (tag, L["size"] / W * 100))
                if L["size"] / W < 0.019: errs.append("%s: text below 1.9%% of width" % tag)
                if L["lang"] == "km" and L["lineHeight"] < 1.5: errs.append("%s: Khmer line-height %.2f" % (tag, L["lineHeight"]))
                if L["x"] < 3 or L["x"] + L["w"] > 97: errs.append("%s: text box outside 3%% safe margin" % tag)
                if L["y"] < 2 or L["y"] + L["h"] > 98: errs.append("%s: text box outside vertical safe area" % tag)
            elif L["type"] in ("svg", "pattern"):
                if not os.path.exists(os.path.join(ROOT, L["src"])): errs.append("%s: missing ornament %s" % (tag, L["src"]))
        # text-vs-text overlap
        T = [L for L in ly if L["type"] == "text"]
        for a in range(len(T)):
            for b in range(a + 1, len(T)):
                A, B = T[a], T[b]
                ox = min(A["x"] + A["w"], B["x"] + B["w"]) - max(A["x"], B["x"])
                oy = min(A["y"] + A["h"], B["y"] + B["h"]) - max(A["y"], B["y"])
                if ox > 0 and oy > 0.8: errs.append("%s p%d: text overlap %s / %s (%.1f%%)" % (tp["id"], pi + 1, A["id"], B["id"], oy))
    for n in tp.get("notes", []): errs.append("%s: %s" % (tp["id"], n))

def main():
    copy = json.load(open(os.path.join(ROOT, "copy-bank.json"), encoding="utf-8"))["copy"]
    for k, v in copy.items():
        if not KH.search(v["km"]): errs.append("copy %s: km has no Khmer" % k)
        if re.search(r"[A-Za-z]", re.sub(r"\[[^\]]*\]", "", v["km"])): errs.append("copy %s: Latin in km" % k)
    files = sorted(glob.glob(os.path.join(ROOT, "templates", "*.json")))
    if len(files) < 30: errs.append("only %d templates (need >= 30)" % len(files))
    for f in files: lint_template(json.load(open(f, encoding="utf-8")), copy)
    # Khmer outside the copy bank (source hygiene)
    for src in ("layouts.py", "catalog.py", "engine.py"):
        t = open(os.path.join(ROOT, "generator", src), encoding="utf-8").read()
        if KH.search(t): errs.append("%s contains literal Khmer" % src)
    for w in warns: print("WARN ", w)
    for e in errs: print("ERROR", e)
    print("%d templates, %d errors, %d warnings" % (len(files), len(errs), len(warns)))
    sys.exit(1 if errs else 0)

if __name__ == "__main__": main()

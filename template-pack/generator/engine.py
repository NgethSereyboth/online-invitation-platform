# -*- coding: utf-8 -*-
"""Layout engine: canvases, palettes, type packs, layer constructors, text measuring, vertical flow."""
import os, re, math

CANVASES = {
    "a5p":   {"w": 1000, "h": 1414, "label": "A5 portrait invitation (1 : 1.414)"},
    "p45":   {"w": 1080, "h": 1350, "label": "4 : 5 social portrait"},
    "sq":    {"w": 1080, "h": 1080, "label": "Square card"},
    "story": {"w": 1080, "h": 1920, "label": "Story / phone full screen (9 : 16)"},
    "land":  {"w": 1600, "h": 900,  "label": "Landscape banner (16 : 9)"},
}

FONTS = {  # role -> Google Fonts family, licence, preview file
    "kh.moul": ("Moul", "OFL-1.1", "moul.ttf"), "kh.moulpali": ("Moulpali", "OFL-1.1", "moulpali.ttf"),
    "kh.koulen": ("Koulen", "OFL-1.1", "koulen.ttf"), "kh.bokor": ("Bokor", "OFL-1.1", "bokor.ttf"),
    "kh.serif": ("Noto Serif Khmer", "OFL-1.1", "nserifk.ttf"), "kh.sans": ("Noto Sans Khmer", "OFL-1.1", "nsk.ttf"),
    "kh.battambang": ("Battambang", "OFL-1.1", "battambang.ttf"), "kh.kantumruy": ("Kantumruy Pro", "OFL-1.1", "kantumruy.ttf"),
    "lat.cormorant": ("Cormorant Garamond", "OFL-1.1", "cormorant.ttf"), "lat.playfair": ("Playfair Display", "OFL-1.1", "playfair.ttf"),
    "lat.script": ("Great Vibes", "OFL-1.1", "greatvibes.ttf"), "lat.cinzel": ("Cinzel", "OFL-1.1", "cinzel.ttf"),
    "lat.montserrat": ("Montserrat", "OFL-1.1", "montserrat.ttf"), "lat.jost": ("Jost", "OFL-1.1", "jost.ttf"),
}

def svg_aspect(src, root):
    txt = open(os.path.join(root, src), encoding="utf-8").read(600)
    m = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"', txt)
    return float(m.group(3)), float(m.group(4))

def hexrgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def lum(h):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = [ch(c) for c in hexrgb(h)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a, b):
    la, lb = lum(a), lum(b)
    if la < lb: la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)

# ---- type packs: role -> (font, size@1000w, weight, lineHeight, letterSpacing em) ----
def pack(kind):
    P = {
     "ceremonial": dict(
        title=("kh.moul", 50, 400, 1.75, 0), title_en=("lat.cinzel", 27, 500, 1.4, .22),
        lead=("kh.serif", 30, 400, 1.95, 0), lead_en=("lat.cormorant", 27, 500, 1.45, .02),
        name=("kh.moulpali", 44, 400, 1.7, 0), name_en=("lat.script", 82, 400, 1.15, 0), amp=("lat.script", 70, 400, 1, 0),
        label=("kh.serif", 27, 600, 1.7, 0), label_en=("lat.cinzel", 21, 500, 1.4, .2),
        date=("kh.serif", 38, 700, 1.8, 0), date_en=("lat.cormorant", 36, 600, 1.3, .08),
        body=("kh.serif", 29, 400, 1.9, 0), body_en=("lat.cormorant", 26, 500, 1.4, .02),
        small=("kh.serif", 25, 400, 1.8, 0), small_en=("lat.cormorant", 23, 500, 1.35, .04)),
     "elegant": dict(
        title=("kh.moulpali", 46, 400, 1.75, 0), title_en=("lat.playfair", 30, 400, 1.35, .14),
        lead=("kh.serif", 29, 400, 1.95, 0), lead_en=("lat.cormorant", 27, 500, 1.45, .02),
        name=("kh.serif", 42, 700, 1.7, 0), name_en=("lat.playfair", 56, 400, 1.2, .02), amp=("lat.cormorant", 54, 500, 1, 0),
        label=("kh.serif", 26, 600, 1.7, 0), label_en=("lat.playfair", 21, 400, 1.4, .2),
        date=("kh.serif", 36, 700, 1.8, 0), date_en=("lat.playfair", 34, 400, 1.3, .1),
        body=("kh.serif", 28, 400, 1.9, 0), body_en=("lat.cormorant", 26, 500, 1.4, .02),
        small=("kh.serif", 24, 400, 1.8, 0), small_en=("lat.cormorant", 22, 500, 1.35, .04)),
     "modern": dict(
        title=("kh.kantumruy", 46, 700, 1.7, 0), title_en=("lat.jost", 26, 500, 1.4, .3),
        lead=("kh.kantumruy", 29, 400, 1.9, 0), lead_en=("lat.jost", 25, 400, 1.5, .02),
        name=("kh.kantumruy", 52, 700, 1.6, 0), name_en=("lat.jost", 60, 300, 1.15, .06), amp=("lat.jost", 44, 300, 1, 0),
        label=("kh.kantumruy", 25, 600, 1.7, 0), label_en=("lat.jost", 21, 500, 1.4, .26),
        date=("kh.kantumruy", 36, 700, 1.7, 0), date_en=("lat.jost", 34, 400, 1.3, .12),
        body=("kh.kantumruy", 27, 400, 1.9, 0), body_en=("lat.jost", 24, 400, 1.5, .02),
        small=("kh.kantumruy", 23, 400, 1.8, 0), small_en=("lat.jost", 22, 400, 1.4, .05)),
     "festive": dict(
        title=("kh.koulen", 62, 400, 1.55, 0), title_en=("lat.montserrat", 30, 700, 1.3, .16),
        lead=("kh.battambang", 32, 400, 1.9, 0), lead_en=("lat.montserrat", 25, 500, 1.5, .02),
        name=("kh.koulen", 56, 400, 1.5, 0), name_en=("lat.montserrat", 54, 800, 1.1, .02), amp=("lat.montserrat", 40, 700, 1, 0),
        label=("kh.battambang", 27, 700, 1.7, 0), label_en=("lat.montserrat", 21, 700, 1.4, .18),
        date=("kh.koulen", 44, 400, 1.6, 0), date_en=("lat.montserrat", 34, 700, 1.3, .1),
        body=("kh.battambang", 29, 400, 1.9, 0), body_en=("lat.montserrat", 24, 500, 1.5, .02),
        small=("kh.battambang", 24, 400, 1.8, 0), small_en=("lat.montserrat", 21, 500, 1.4, .06)),
    }
    return P[kind]

class Measurer:
    """Measures wrapped text height with real fonts when PACK_FONTS is set, else estimates."""
    def __init__(self):
        self.dir = os.environ.get("PACK_FONTS")
        self.cache = {}
        self.ok = False
        if self.dir:
            try:
                from PIL import ImageFont, features
                self.ImageFont = ImageFont
                self.ok = features.check("raqm")
            except Exception:
                self.ok = False

    def font(self, role, size, weight):
        key = (role, round(size), weight)
        if key in self.cache: return self.cache[key]
        ft = self.ImageFont.truetype(os.path.join(self.dir, FONTS[role][2]), max(8, round(size)), layout_engine=self.ImageFont.Layout.RAQM)
        try:
            axes = ft.get_variation_axes()
            vals = []
            for a in axes:
                nm = a.get("name", b"")
                nm = nm.decode() if isinstance(nm, bytes) else str(nm)
                if "eight" in nm: vals.append(max(a["minimum"], min(a["maximum"], weight)))
                else: vals.append(a["default"])
            ft.set_variation_by_axes(vals)
        except Exception:
            pass
        self.cache[key] = ft
        return ft

    def width(self, role, size, weight, text, ls=0):
        if not self.ok:
            return len(text) * size * (0.92 if re.search(r"[\u1780-\u17ff]", text) else 0.5) * (1 + ls)
        ft = self.font(role, size, weight)
        return ft.getlength(text, language="km" if re.search(r"[\u1780-\u17ff]", text) else "en") + ls * size * len(text)

    def wrap(self, role, size, weight, text, boxw, ls=0):
        """Greedy wrap; break opportunities are spaces and U+200B (Khmer word boundaries)."""
        toks = re.findall(r"[^ \u200b]+[ \u200b]?", text)
        lines, cur = [], ""
        clean = lambda x: x.replace("\u200b", "").strip()
        for w in toks:
            t = cur + w
            if cur and self.width(role, size, weight, clean(t), ls) > boxw:
                lines.append(clean(cur)); cur = w
            else:
                cur = t
        lines.append(clean(cur))
        return lines

M = Measurer()

class Block:
    def __init__(self, h, fn, tag=""):
        self.h, self.fn, self.tag = h, fn, tag

class T:
    """Template builder for one canvas + palette + type pack."""
    def __init__(self, tid, canvas, palette, kind, copy, root):
        self.id, self.cv, self.pal, self.copy, self.root = tid, CANVASES[canvas], palette, copy, root
        self.canvas, self.ty = canvas, pack(kind)
        self.W, self.H = self.cv["w"], self.cv["h"]
        self.k = self.W / 1000.0
        self.layers, self.n, self.notes = [], 0, []
        self.photos = []

    # -- primitives --
    def _id(self, p):
        self.n += 1
        return "%s-%02d" % (p, self.n)

    def add(self, layer, name=None):
        layer["id"] = self._id(layer["type"])
        if name: layer["name"] = name
        layer.setdefault("rot", 0); layer.setdefault("opacity", 1)
        self.layers.append(layer)
        return layer

    def bg(self, fill="bg", name="Background"):
        return self.add({"type": "bg", "x": 0, "y": 0, "w": 100, "h": 100, "fill": fill}, name)

    def rect(self, x, y, w, h, fill=None, stroke=None, sw=0, radius=0, opacity=1, name=None, shape="rect"):
        return self.add({"type": "shape", "shape": shape, "x": x, "y": y, "w": w, "h": h, "fill": fill, "stroke": stroke,
                         "strokeWidth": sw * self.k, "radius": radius * self.k, "opacity": opacity}, name)

    def line(self, x, y, w, color="accent", sw=2, opacity=1, name="Rule"):
        return self.rect(x, y, w, 0, None, color, sw, 0, opacity, name, "line")

    def svg(self, src, x, y, w, color="accent", rot=0, flipx=False, flipy=False, opacity=1, name=None, recolor=None, anchor="tl", h=None):
        vw, vh = svg_aspect("ornaments/%s.svg" % src, self.root)
        hh = h if h is not None else (w / 100 * self.W) * vh / vw / self.H * 100
        if anchor == "c": x, y = x - w / 2, y - hh / 2
        elif anchor == "tc": x = x - w / 2
        elif anchor == "bc": x, y = x - w / 2, y - hh
        elif anchor == "br": x, y = x - w, y - hh
        elif anchor == "tr": x = x - w
        elif anchor == "bl": y = y - hh
        d = {"type": "svg", "src": "ornaments/%s.svg" % src, "x": round(x, 2), "y": round(y, 2), "w": w, "h": round(hh, 2),
             "color": color, "rot": rot, "flipX": flipx, "flipY": flipy, "opacity": opacity}
        if recolor: d["recolor"] = recolor
        return self.add(d, name or src)

    def pattern(self, src, color="accent", tile=90, opacity=0.08, name="Pattern"):
        return self.add({"type": "pattern", "src": "ornaments/%s.svg" % src, "x": 0, "y": 0, "w": 100, "h": 100,
                         "tile": tile * self.k, "color": color, "opacity": opacity}, name)

    def photo(self, slot, x, y, w, h, shape="rect", frame=None, fw=4, name=None):
        d = {"type": "photo", "slot": slot, "shape": shape, "x": x, "y": y, "w": w, "h": h, "placeholder": "photo-" + slot,
             "frame": ({"color": frame, "width": fw * self.k} if frame else None)}
        self.photos.append(slot)
        return self.add(d, name or "Photo " + slot)

    # -- text --
    def text_layers(self, key, role, x, w, color, align="center", lang=None, literal=None, y=0, size_mul=1, weight=None,
                    upper=False, name=None, slot=None, maxw=None):
        font, size, wt, lh, ls = self.ty[role]
        size = size * self.k * size_mul
        if weight: wt = weight
        lang = lang or ("km" if role in ("title", "lead", "name", "label", "date", "body", "small") else "en")
        if lang == "km": ls = 0  # never letter-space Khmer: it breaks clusters
        txt = literal if literal is not None else self.copy[key][lang]
        boxw = w / 100 * self.W
        lines = M.wrap(font, size, wt, txt.upper() if upper else txt, boxw, ls)
        hpx = len(lines) * size * lh
        hpct = hpx / self.H * 100
        L = {"type": "text", "x": x, "y": y, "w": w, "h": round(hpct, 2), "lang": lang, "font": font, "size": round(size, 1),
             "weight": wt, "color": color, "align": align, "lineHeight": lh, "letterSpacing": ls, "transform": "upper" if upper else "none",
             "lines": len(lines)}
        if key: L["copy"] = key
        else: L["literal"] = literal
        if slot: L["slot"] = slot
        return L, hpct

    def t(self, key, role, color="ink", x=10, w=80, align="center", lang=None, literal=None, size_mul=1, weight=None,
          upper=False, name=None, slot=None, lead=0):
        L, hp = self.text_layers(key, role, x, w, color, align, lang, literal, 0, size_mul, weight, upper, name, slot)
        def make(y, L=L, name=name):
            L2 = dict(L); L2["y"] = round(y, 2)
            self.add(L2, name or (L2.get("copy") or L2.get("literal", ""))[:28])
        return Block(hp, make, "text")

    def bi(self, key_km, key_en, rk, re_, ck="ink", ce=None, x=10, w=80, gap=0.4, align="center", slot=None, size_mul=1, upper_en=False):
        """Bilingual pair: Khmer line over English line."""
        b1 = self.t(key_km, rk, ck, x, w, align, "km", slot=slot, size_mul=size_mul)
        b2 = self.t(key_en, re_, ce or ck, x, w, align, "en", size_mul=size_mul, upper=upper_en, slot=(slot + "_en") if slot else None)
        return Block(b1.h + gap + b2.h, lambda y: (b1.fn(y), b2.fn(y + b1.h + gap)), "bi")

    def gap(self, h):
        return Block(h, lambda y: None, "gap")

    def orn(self, src, w, color="accent", x=50, **kw):
        vw, vh = svg_aspect("ornaments/%s.svg" % src, self.root)
        hh = (w / 100 * self.W) * vh / vw / self.H * 100
        return Block(hh, lambda y: self.svg(src, x, y, w, color, anchor="tc", **kw), "svg")

    def stack(self, blocks, y0, y1, mingap=0.6, maxgap=3.2, valign="center"):
        total = sum(b.h for b in blocks)
        n = max(1, len(blocks) - 1)
        free = (y1 - y0) - total
        gap = free / n if n else 0
        if free < 0 or gap < mingap * (0.4 if any(b.tag == "gap" for b in blocks) else 1):
            if free < 0:
                self.notes.append("OVERFLOW %.1f%% in stack %s..%s (blocks %.1f%%)" % (-free, y0, y1, total))
            gap = max(gap, 0)
        start = y0
        if gap > maxgap:
            start = y0 + (free - maxgap * n) / 2
            gap = maxgap
        y = start
        for b in blocks:
            b.fn(y)
            y += b.h + gap
        return y

    def spec(self):
        return self.layers

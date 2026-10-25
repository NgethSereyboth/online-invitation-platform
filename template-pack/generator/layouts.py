# -*- coding: utf-8 -*-
"""Composition archetypes. Each builder fills a T (engine.T) with layers using only palette roles."""
from engine import Block

def row(t, cols):
    """cols: list of (x, w, Block). Aligns blocks on the same y."""
    h = max(b.h for _, _, b in cols)
    return Block(h, lambda y: [b.fn(y) for _, _, b in cols], "row")

def info(t, o, km_role="date", en_role="date_en", keys=None, x=14, w=72):
    """Date (large) over a time | venue row. `keys` kept for call compatibility."""
    c = o.get("c", {})
    d = t.bi("ph.date", "ph.date", km_role, en_role, c.get("date", "accent"), c.get("date_en", c.get("date", "accent")), x=x, w=w, gap=0.2)
    bc, bce = c.get("body", "ink"), c.get("body_en", c.get("body", "ink"))
    tm = t.bi("ph.time", "ph.time", "body", "body_en", bc, bce, x=x, w=w * 0.44, gap=0.2)
    ve = t.bi("ph.venue", "ph.venue", "body", "body_en", bc, bce, x=x + w * 0.56, w=w * 0.44, gap=0.2)
    return [d, t.gap(0.4), row(t, [(0, 0, tm), (0, 0, ve)])]

def frame(t, c, o, key="frame"):
    """A5 ornamental frame on A5 canvases, double hairline rectangle elsewhere (the SVG frame letterboxes)."""
    col_ = c.get(key, "accent")
    if abs(t.H / t.W - 1.414) < .02:
        t.svg("frame-a5", 3, 2.1, 94, col_, h=95.8, name="Frame")
    else:
        m = 3.6; t.rect(m, m * t.W / t.H, 100 - 2 * m, 100 - 2 * m * t.W / t.H, None, col_, 3, 0, 1, "Frame outer")
        m = 5.2; t.rect(m, m * t.W / t.H, 100 - 2 * m, 100 - 2 * m * t.W / t.H, None, col_, 1.4, 0, .7, "Frame inner")

def corners(t, src, inset=3.4, w=17, color="accent", op=1):
    k = w
    t.svg(src, inset, inset * t.W / t.H if t.H > t.W else inset, k, color, opacity=op, name="Corner TL")
    ph = k / 100 * t.W
    t.svg(src, 100 - inset, inset * t.W / t.H if t.H > t.W else inset, k, color, flipx=True, opacity=op, anchor="tr", name="Corner TR")
    t.svg(src, inset, 100 - (inset * t.W / t.H if t.H > t.W else inset), k, color, flipy=True, opacity=op, anchor="bl", name="Corner BL")
    t.svg(src, 100 - inset, 100 - (inset * t.W / t.H if t.H > t.W else inset), k, color, flipx=True, flipy=True, opacity=op, anchor="br", name="Corner BR")

def names(t, c, o, mul=1.0, x=10, w=80, amp_x=40):
    """Couple (groom & bride) or a single name block when o['single'] is a copy key."""
    nm, nmen = c.get("name", "ink"), c.get("name_en", c.get("name", "ink"))
    if o.get("single"):
        return [t.bi(o["single"], o["single"], "name", "name_en", nm, nmen, x=x, w=w, gap=0.1, size_mul=mul, slot="name")]
    return [t.bi("ph.groom", "ph.groom", "name", "name_en", nm, nmen, x=x, w=w, gap=0.1, size_mul=mul, slot="groom"),
            t.t(None, "amp", c.get("amp", "accent"), x=amp_x, w=100 - 2 * amp_x, literal="&", lang="en", size_mul=mul),
            t.bi("ph.bride", "ph.bride", "name", "name_en", nm, nmen, x=x, w=w, gap=0.1, size_mul=mul, slot="bride")]

# ---------------------------------------------------------------- 1 ceremony
def ceremony(t, o):
    c = o.get("c", {})
    t.bg(o.get("bg", "bg"))
    if o.get("pattern"): t.pattern("lattice-tile", c.get("pat", "accent"), 84, o.get("pat_op", 0.06))
    if o.get("frame", True): frame(t, c, o)
    if o.get("corner"): corners(t, o["corner"], 4.6, o.get("corner_w", 17), c.get("corner", "accent"))
    blocks = [t.orn(o.get("emblem", "lotus-solid"), o.get("emblem_w", 15), c.get("emblem", "accent"), x=50),
              t.bi(o.get("title", "wedding.title"), o.get("title", "wedding.title"), "title", "title_en", c.get("title", "accent"),
                   c.get("title_en", c.get("title", "accent")), w=84, gap=0.5, upper_en=True),
              t.orn("divider-diamond", 34, c.get("line", "accent"), x=50),
              t.bi(o.get("lead", "wedding.invite_short"), o.get("lead", "wedding.invite_short"), "lead", "lead_en", c.get("body", "ink"), c.get("body_en", c.get("body", "ink")), x=12, w=76, gap=0.4),
              t.gap(1.2)]
    blocks += names(t, c, o, o.get("name_mul", .88))
    blocks.append(t.orn("divider-lotus", 40, c.get("line", "accent"), x=50))
    blocks += info(t, o)
    blocks.append(t.t("label.rsvp", "small", c.get("soft", c.get("body", "ink")), x=15, w=70, lang="km"))
    t.stack(blocks, o.get("y0", 6.5), o.get("y1", 91.5))

# ---------------------------------------------------------------- 2 arch (temple gate)
def arch(t, o):
    c = o.get("c", {})
    t.bg(o.get("bg", {"gradient": {"angle": 180, "stops": [["sky", 0], ["bg", 1]]}}))
    t.svg("arch-pointed", 10, 4, 80, c.get("arch", "accent"), name="Arch", h=66)
    if o.get("skyline", True):
        t.svg("prasat-skyline", 50, 100, 66, c.get("sky", "accent"), opacity=o.get("sky_op", .9), anchor="bc", name="Temple skyline")
    if o.get("sun"): t.svg("sun-medallion", 50, 18, 22, c.get("sun", "accent2"), opacity=.28, anchor="c", name="Sun halo")
    blocks = [t.orn("lotus-solid", 11, c.get("emblem", "accent"), x=50),
              t.bi(o.get("title", "wedding.title"), o.get("title", "wedding.title"), "title", "title_en", c.get("title", "ink"), c.get("title_en", "soft"), x=27, w=46, gap=.9, upper_en=True, size_mul=.78),
              t.gap(1.2)]
    blocks += names(t, c, o, 0.78, 24, 52)
    t.stack(blocks, 17, 62)
    t.stack(info(t, o, x=14, w=72), 68, 84)

# ---------------------------------------------------------------- 3 minimal
def minimal(t, o):
    c = o.get("c", {})
    t.bg(o.get("bg", "bg"))
    if o.get("corner"):
        t.svg("corner-simple", 6, 4.3, 10, c.get("line", "accent"), name="Corner TL")
        t.svg("corner-simple", 94, 95.7, 10, c.get("line", "accent"), flipx=True, flipy=True, anchor="br", name="Corner BR")
    top = [t.bi(o.get("kicker", "label.save_the_date"), o.get("kicker", "label.save_the_date"), "label", "label_en", c.get("soft", "soft"), c.get("soft", "soft"), x=15, w=70, gap=.3, upper_en=True)]
    mid = names(t, c, o, o.get("name_mul", 1.0))
    t.stack(top, 7.5, 15.5)
    t.line(42, 21, 16, c.get("line", "accent"), 2)
    t.stack(mid, 22, 59)
    t.line(42, 61.5, 16, c.get("line", "accent"), 2)
    cols = []
    for i, k in enumerate(("ph.date", "ph.time", "ph.venue")):
        cols.append((8 + i * 29.5, 27, t.bi(k, k, "label", "label_en", c.get("body", "ink"), c.get("body", "ink"), x=8 + i * 29.5, w=27, gap=.3)))
    t.stack([row(t, cols)], 66, 74)
    t.stack([t.bi(o.get("lead", "wedding.invite_short"), o.get("lead", "wedding.invite_short"), "body", "body_en", c.get("body", "ink"), c.get("soft", "soft"), x=14, w=72, gap=.4),
             t.t("label.rsvp", "small", c.get("soft", "soft"), x=15, w=70, lang="km")], 76, 95)

# ---------------------------------------------------------------- 4 photo
def photo(t, o):
    c = o.get("c", {})
    t.bg(o.get("bg", "bg"))
    t.photo("couple", 0, 0, 100, 42, "rect", name="Couple photo")
    t.rect(0, 37, 100, 70, o.get("panel", "paper"), None, 0, 70, 1, "Sheet")
    t.svg("lotus-solid", 50, 35.6, 9, c.get("emblem", "accent"), anchor="c", name="Emblem")
    blocks = [t.bi(o.get("title", "wedding.title"), o.get("title", "wedding.title"), "title", "title_en", c.get("title", "accent"), c.get("title", "accent"), x=14, w=72, gap=.9, upper_en=True, size_mul=.8),
              ] + names(t, c, o, .74)
    blocks += info(t, {"c": {"date": c.get("accent", "accent"), "body": c.get("body", "ink")}}, x=14, w=72)
    t.stack(blocks, 41.5, 95)

# ---------------------------------------------------------------- 5 medallion
def medallion(t, o):
    c = o.get("c", {})
    t.bg(o.get("bg", "bg"))
    if o.get("pattern"): t.pattern("lattice-tile", c.get("pat", "accent"), 84, o.get("pat_op", .06))
    if o.get("frame"): frame(t, c, o)
    t.svg("sun-medallion", 50, 16.5, o.get("sun_w", 44), c.get("sun", "accent"), opacity=o.get("sun_op", .95), anchor="c", name="Medallion")
    t.stack([t.bi(o.get("title", "wedding.title"), o.get("title", "wedding.title"), "title", "title_en", c.get("title", "ink"), c.get("title_en", c.get("title", "ink")), x=12, w=76, gap=.9, upper_en=True)], 28, 38)
    blocks = [t.bi(o.get("lead", "wedding.invite_short"), o.get("lead", "wedding.invite_short"), "lead", "lead_en", c.get("body", "ink"), c.get("body", "ink"), x=12, w=76, gap=.3),
              t.gap(1)] + names(t, c, o, .85)
    t.stack(blocks, 40, 74)
    t.stack([t.orn("divider-lotus", 36, c.get("line", "accent"), x=50)] + info(t, {"c": {"date": c.get("date", "accent"), "body": c.get("body", "ink")}}, x=14, w=72), 76, 94)

# ---------------------------------------------------------------- 6 watercolour / soft
def soft(t, o):
    c = o.get("c", {})
    t.bg(o.get("bg", "bg"))
    t.svg("watercolour-wash", -8, -6, 70, "accent", recolor={"c1": o.get("w1", "accent"), "c2": o.get("w2", "accent2")}, name="Wash top", opacity=.85)
    t.svg("watercolour-wash", 38, 62, 80, "accent", recolor={"c1": o.get("w2", "accent2"), "c2": o.get("w1", "accent")}, name="Wash bottom", opacity=.8, flipx=True)
    for i, (src, x, y, w, fl) in enumerate(o.get("decor", [("champei", 8, 6, 14, False), ("champei", 80, 88, 12, True)])):
        t.svg(src, x, y, w, c.get("decor", "accent"), flipx=fl, name="Decor %d" % (i + 1), opacity=.95)
    blocks = [t.orn(o.get("emblem", "lotus-line"), 17, c.get("emblem", "accent"), x=50),
              t.bi(o["title"], o["title"], "title", "title_en", c.get("title", "ink"), c.get("title_en", c.get("title", "ink")), x=12, w=76, gap=.9, upper_en=True)]
    if o.get("name"):
        blocks.append(t.bi(o["name"], o["name"], "name", "name_en", c.get("name", "ink"), c.get("name", "ink"), x=10, w=80, gap=0, slot="name"))
    if o.get("couple"): blocks += names(t, c, {}, .9)
    blocks.append(t.orn("divider-lotus", 36, c.get("line", "accent"), x=50))
    blocks.append(t.bi(o["line"], o["line"], "lead", "lead_en", c.get("body", "ink"), c.get("body", "ink"), x=13, w=74, gap=.4))
    if o.get("info"): blocks += info(t, {"c": {"date": c.get("date", "accent"), "body": c.get("body", "ink")}}, x=14, w=72)
    if o.get("closing"): blocks.append(t.bi(o["closing"], o["closing"], "small", "small_en", c.get("soft", "soft"), c.get("soft", "soft"), x=15, w=70, gap=.2))
    t.stack(blocks, 9, 91)

# ---------------------------------------------------------------- 7 luxe (dark, gold lines)
def luxe(t, o):
    c = o.get("c", {})
    t.bg(o.get("bg", "bg"))
    if o.get("pattern"): t.pattern("lattice-tile", c.get("pat", "accent"), 90, .05)
    m = 3.6
    t.rect(m, m * t.W / t.H, 100 - 2 * m, 100 - 2 * m * t.W / t.H, None, c.get("frame", "accent"), 3, 0, 1, "Frame outer")
    m2 = 5.3
    t.rect(m2, m2 * t.W / t.H, 100 - 2 * m2, 100 - 2 * m2 * t.W / t.H, None, c.get("frame", "accent"), 1.4, 0, .7, "Frame inner")
    blocks = [t.orn(o.get("emblem", "starburst"), o.get("emblem_w", 26), c.get("emblem", "accent"), x=50),
              t.bi(o["title"], o["title"], "title", "title_en", c.get("title", "accent"), c.get("title_en", "ink"), x=12, w=76, gap=.9, upper_en=True),
              t.orn("divider-diamond", 32, c.get("line", "accent"), x=50)]
    if o.get("lead"): blocks.append(t.bi(o["lead"], o["lead"], "lead", "lead_en", c.get("body", "ink"), c.get("body", "ink"), x=13, w=74, gap=.3))
    if o.get("couple"): blocks += names(t, c, {}, o.get("name_mul", .9))
    elif o.get("host"):
        blocks.append(t.bi(o["host"], o["host"], "name", "name_en", c.get("name", "ink"), c.get("name", "ink"), x=10, w=80, gap=0, size_mul=.9, slot="host"))
    blocks.append(t.orn("divider-diamond", 32, c.get("line", "accent"), x=50))
    blocks += info(t, {"c": {"date": c.get("date", "accent"), "body": c.get("body", "ink")}}, x=14, w=72)
    if o.get("rsvp", True): blocks.append(t.t("label.rsvp", "small", c.get("soft", "soft"), x=15, w=70, lang="km"))
    t.stack(blocks, 9, 91)

# ---------------------------------------------------------------- 8 greeting card
def greeting(t, o):
    c = o.get("c", {})
    t.bg(o.get("bg", "bg"))
    if o.get("pattern"): t.pattern("lattice-tile", c.get("pat", "accent"), 90, .06)
    if o.get("top_strip", True): t.svg("kbach-strip", 0, 0, 100, c.get("strip", "accent"), name="Border top", opacity=.95)
    if o.get("bottom_strip", True): t.svg("kbach-strip", 0, 100, 100, c.get("strip", "accent"), flipy=True, anchor="bl", name="Border bottom", opacity=.95)
    for i, d in enumerate(o.get("decor", [])):
        src, x, y, w = d[:4]
        kw = d[4] if len(d) > 4 else {}
        t.svg(src, x, y, w, kw.pop("color", c.get("decor", "accent")), name="Decor %d" % (i + 1), **kw)
    land = t.W > t.H
    xs, ws = (6, 54) if land else (9, 82)
    blocks = []
    if o.get("emblem"): blocks.append(t.orn(o["emblem"], o.get("emblem_w", 16), c.get("emblem", "accent"), x=xs + ws / 2))
    blocks.append(t.bi(o["title"], o["title"], "title", "title_en", c.get("title", "accent"), c.get("title_en", "ink"), x=xs, w=ws, gap=.9, upper_en=True, size_mul=o.get("tmul", 1.0)))
    blocks.append(t.orn(o.get("div", "divider-diamond"), 30 if not land else 22, c.get("line", "accent"), x=xs + ws / 2))
    if o.get("greet"): blocks.append(t.bi(o["greet"], o["greet"], "lead", "lead_en", c.get("body", "ink"), c.get("body", "ink"), x=xs, w=ws, gap=.3))
    blocks.append(t.bi(o["line"], o["line"], "lead", "lead_en", c.get("body", "ink"), c.get("body", "ink"), x=xs + 2, w=ws - 4, gap=.3))
    if o.get("name"): blocks.append(t.bi(o["name"], o["name"], "name", "name_en", c.get("name", "accent"), c.get("name", "accent"), x=xs, w=ws, gap=0, size_mul=.7, slot="name"))
    if o.get("closing"): blocks.append(t.bi(o["closing"], o["closing"], "small", "small_en", c.get("soft", "soft"), c.get("soft", "soft"), x=xs, w=ws, gap=.2))
    t.stack(blocks, o.get("y0", 12), o.get("y1", 88), maxgap=o.get("maxgap", 6))

# ---------------------------------------------------------------- 9 programme page
def programme(t, o):
    c = o.get("c", {})
    t.bg(o.get("bg", "bg"))
    if o.get("pattern"): t.pattern("lattice-tile", c.get("pat", "accent"), 84, o.get("pat_op", .06))
    if o.get("frame", True): frame(t, c, o)
    if o.get("corner"): corners(t, o["corner"], 4.6, 15, c.get("corner", "accent"))
    head = [t.orn("lotus-line", 13, c.get("emblem", "accent"), x=50),
            t.bi(o["title"], o["title"], "title", "title_en", c.get("title", "accent"), c.get("title_en", c.get("title", "accent")), x=12, w=76, gap=.9, upper_en=True, size_mul=.8),
            t.orn("divider-lotus", 38, c.get("line", "accent"), x=50)]
    t.stack(head, 8, 28)
    rows = o["rows"]
    n = len(rows)
    y0, y1 = 31, 86
    step = (y1 - y0) / n
    for i, (tkey, ikey) in enumerate(rows):
        y = y0 + i * step
        left = t.bi("label." + tkey, "label." + tkey, "label", "label_en", c.get("date", "accent"), c.get("date", "accent"), x=10, w=22, gap=.2, align="left")
        left2 = t.t("ph.time", "body", c.get("body", "ink"), x=10, w=22, lang="km", align="left")
        right = t.bi(ikey, ikey, "body", "body_en", c.get("body", "ink"), c.get("soft", "soft"), x=36, w=54, gap=.2, align="left")
        h = max(left.h + .2 + left2.h, right.h)
        yy = y + (step - h) / 2 - 1.2
        left.fn(yy); left2.fn(yy + left.h + .2); right.fn(yy)
        if i < n - 1: t.line(10, y + step - 1.2, 80, c.get("line", "accent"), 1.4, .6, "Row rule")
    t.stack([t.t("label.rsvp", "small", c.get("soft", "soft"), x=15, w=70, lang="km")], 89, 94)

# ---------------------------------------------------------------- 10 party pop
def party(t, o):
    c = o.get("c", {})
    t.bg(o.get("bg", "bg"))
    t.svg("confetti", 0, 0, 100, "accent", recolor=o.get("confetti", {"c1": "accent", "c2": "accent2", "c3": "deep"}), opacity=.45, name="Confetti", h=100)
    t.svg("balloons", 98, 94, 30, "accent", recolor=o.get("balloons", {"c1": "accent", "c2": "accent2", "c3": "deep"}), anchor="br", name="Balloons")
    blocks = [t.bi(o["title"], o["title"], "title", "title_en", c.get("title", "deep"), c.get("title_en", "deep"), x=8, w=84, gap=.9, upper_en=True, size_mul=o.get("tmul", 1.0))]
    if o.get("name"): blocks.append(t.bi(o["name"], o["name"], "name", "name_en", c.get("name", "accent"), c.get("name", "accent"), x=8, w=84, gap=0, slot="name"))
    blocks.append(t.bi(o["line"], o["line"], "lead", "lead_en", c.get("body", "ink"), c.get("body", "ink"), x=10, w=80, gap=.3))
    blocks += info(t, {"c": {"date": c.get("date", "deep"), "body": c.get("body", "ink")}}, x=12, w=76)
    t.rect(0, 100 - 5, 100, 5, o.get("bar", "deep"), None, 0, 0, 1, "Base bar")
    t.stack(blocks, 8, 74)

# ---------------------------------------------------------------- 11 memorial
def memorial(t, o):
    c = o.get("c", {})
    t.bg(o.get("bg", "bg"))
    if o.get("frame", True): t.rect(4.5, 3.2, 91, 93.6, None, c.get("frame", "line"), 2, 0, .8, "Frame")
    blocks = [t.orn(o.get("emblem", "lotus-line"), 14, c.get("emblem", "accent"), x=50),
              t.bi(o["title"], o["title"], "title", "title_en", c.get("title", "ink"), c.get("title_en", "soft"), x=10, w=80, gap=.9, upper_en=True, size_mul=.82)]
    t.stack(blocks, 7, 24)
    if o.get("portrait", True):
        t.photo("portrait", 33, 26.5, 34, 34 * t.W / t.H, "ellipse", c.get("frame", "line"), 4, "Portrait")
        py = 26.5 + 34 * t.W / t.H + 2.5
    else:
        cl = t.svg("candle", 50, 28, 5.5, c.get("emblem", "accent"), anchor="tc", name="Candle"); py = cl["y"] + cl["h"] + 2.5
    body = [t.bi(o["name"], o["name"], "name", "name_en", c.get("name", "ink"), c.get("name", "ink"), x=10, w=80, gap=0, size_mul=.82, slot="name"),
            t.orn("divider-diamond", 26, c.get("line", "line"), x=50),
            t.bi(o["line"], o["line"], "lead", "lead_en", c.get("body", "ink"), c.get("soft", "soft"), x=12, w=76, gap=.3)]
    if o.get("info", True): body += info(t, {"c": {"date": c.get("date", "ink"), "body": c.get("body", "ink")}}, x=14, w=72)
    if o.get("wish"): body.append(t.bi(o["wish"], o["wish"], "small", "small_en", c.get("soft", "soft"), c.get("soft", "soft"), x=14, w=72, gap=.2))
    t.stack(body, py, 93)

# ---------------------------------------------------------------- 12 ribbon (business)
def ribbon(t, o):
    c = o.get("c", {})
    t.bg(o.get("bg", "bg"))
    if o.get("pattern"): t.pattern("lattice-tile", c.get("pat", "accent"), 90, .05)
    t.svg("starburst", 50, 22, 62, c.get("burst", "accent"), opacity=.18, anchor="c", name="Burst")
    t.svg("ribbon-banner", 50, 36, 86, c.get("ribbon", "accent"), anchor="c", name="Ribbon")
    blocks = [t.bi(o["title"], o["title"], "title", "title_en", c.get("title", "ink"), c.get("title_en", "ink"), x=14, w=72, gap=.4, upper_en=True, size_mul=.78)]
    t.stack(blocks, 32, 40)
    mid = [t.bi(o["lead"], o["lead"], "lead", "lead_en", c.get("body", "ink"), c.get("body", "ink"), x=12, w=76, gap=.3),
           t.bi("ph.company" if o.get("company", True) else "ph.host", "ph.company" if o.get("company", True) else "ph.host", "name", "name_en", c.get("name", "accent"), c.get("name", "accent"), x=10, w=80, gap=0, size_mul=.85, slot="host")]
    t.stack(mid, 46, 67)
    t.stack([t.orn("divider-diamond", 30, c.get("line", "accent"), x=50)] + info(t, {"c": {"date": c.get("date", "accent"), "body": c.get("body", "ink")}}, x=14, w=72), 69, 94)

BUILDERS = dict(ceremony=ceremony, arch=arch, minimal=minimal, photo=photo, medallion=medallion, soft=soft, luxe=luxe,
                greeting=greeting, programme=programme, party=party, memorial=memorial, ribbon=ribbon)

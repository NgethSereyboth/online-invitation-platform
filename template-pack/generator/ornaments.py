"""Original SVG ornaments for the OKID template pack.

Every shape here is generated from geometry (petals, tapered spirals, polygons). Nothing is traced or copied
from any existing artwork. Monotone ornaments use `currentColor`; the three multi-tone ones use the magic
recolour hexes #AA0001 / #AA0002 / #AA0003 (see template-pack/README.md).
"""
import math, os

def f(n):
    return ("%.1f" % n).rstrip("0").rstrip(".")

def pts(points):
    return " ".join("%s,%s" % (f(x), f(y)) for x, y in points)

def svg(vb, body, extra=""):
    w, h = vb
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" %s>\n%s\n</svg>\n'
            % (f(w), f(h), extra, body))

# ---------- geometry helpers ----------
def petal(h, w, hollow=0.0):
    """Pointed petal, base at (0,0), tip at (0,-h). hollow>0 adds an inner petal cut-out (evenodd)."""
    d = ("M0,0 C%s,%s %s,%s 0,%s C%s,%s %s,%s 0,0Z"
         % (f(w * 1.1), f(-h * 0.22), f(w * 0.9), f(-h * 0.78), f(-h),
            f(-w * 0.9), f(-h * 0.78), f(-w * 1.1), f(-h * 0.22)))
    if hollow:
        hh, ww = h * hollow, w * hollow
        oy = h * 0.14
        d += (" M0,%s C%s,%s %s,%s 0,%s C%s,%s %s,%s 0,%sZ"
              % (f(-oy), f(ww * 1.1), f(-oy - hh * 0.22), f(ww * 0.9), f(-oy - hh * 0.78), f(-oy - hh),
                 f(-ww * 0.9), f(-oy - hh * 0.78), f(-ww * 1.1), f(-oy - hh * 0.22), f(-oy)))
    return d

def taper(center, w0, w1=0.4, power=0.9):
    """Polygon for a tapered stroke along `center` (list of (x,y)). Thick w0 at start, thin w1 at the tip."""
    n = len(center)
    left, right = [], []
    for i, (x, y) in enumerate(center):
        a = center[max(i - 1, 0)]
        b = center[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        t = i / (n - 1)
        hw = w1 + (w0 - w1) * (1 - t) ** power
        left.append((x + nx * hw, y + ny * hw))
        right.append((x - nx * hw, y - ny * hw))
    return left + right[::-1]

def curve(p0, ang, length, bend, curl=0.0, steps=48):
    """Centre line starting at p0 heading `ang` degrees, gently bending, optional spiral curl at the tail."""
    x, y = p0
    a = math.radians(ang)
    out = [(x, y)]
    ds = length / steps
    for i in range(steps):
        t = i / steps
        a += math.radians(bend) / steps + math.radians(curl) * (t ** 3) / steps * 6
        x += math.cos(a) * ds
        y += math.sin(a) * ds
        out.append((x, y))
    return out

def poly(points, extra='fill="currentColor"'):
    return '<polygon points="%s" %s/>' % (pts(points), extra)

def rot(points, deg, cx=0, cy=0):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in points]

def diamond(cx, cy, r):
    return [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]

# ---------- ornaments ----------
def lotus_solid():
    base = (120, 150)
    parts = []
    for ang, h, w in [(-62, 74, 24), (62, 74, 24), (-40, 96, 25), (40, 96, 25), (-19, 112, 26), (19, 112, 26)]:
        parts.append('<path transform="translate(%s,%s) rotate(%s)" d="%s" fill="currentColor" fill-rule="evenodd" opacity="0.88"/>'
                     % (base[0], base[1], ang, petal(h, w, 0.5)))
    parts.append('<path transform="translate(%s,%s)" d="%s" fill="currentColor" fill-rule="evenodd"/>'
                 % (base[0], base[1], petal(128, 27, 0.5)))
    parts.append('<path d="M70,152 C92,160 148,160 170,152 C150,170 90,170 70,152Z" fill="currentColor"/>')
    return svg((240, 172), "\n".join(parts))

def lotus_line():
    base = (120, 150)
    parts = []
    for ang, h, w in [(-62, 74, 24), (62, 74, 24), (-40, 96, 25), (40, 96, 25), (-19, 112, 26), (19, 112, 26), (0, 128, 27)]:
        parts.append('<path transform="translate(%s,%s) rotate(%s)" d="%s" fill="none" stroke="currentColor" stroke-width="3" stroke-linejoin="round"/>'
                     % (base[0], base[1], ang, petal(h, w)))
    parts.append('<path transform="translate(120,150)" d="M0,-10 C6,-40 6,-80 0,-108" fill="none" stroke="currentColor" stroke-width="2.2"/>')
    parts.append('<path d="M72,154 C94,164 146,164 168,154" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>')
    return svg((240, 172), "\n".join(parts))

def lotus_bud():
    parts = ['<path transform="translate(60,150)" d="%s" fill="currentColor" fill-rule="evenodd"/>' % petal(130, 28, 0.5)]
    for sgn in (-1, 1):
        parts.append('<path transform="translate(60,150) rotate(%s)" d="%s" fill="currentColor" opacity="0.85"/>' % (sgn * 26, petal(96, 22)))
    parts.append('<path d="M60,150 C58,170 62,186 60,200" stroke="currentColor" stroke-width="3" fill="none" stroke-linecap="round"/>')
    return svg((120, 204), "\n".join(parts))

def flame(origin, ang, length, bend, curl, w0):
    return poly(taper(curve(origin, ang, length, bend, curl), w0, 0.5))



def divider_lotus():
    parts = ['<path d="M20,30 H236 M364,30 H580" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>']
    parts.append('<g transform="translate(300,56) scale(0.3) translate(-120,-150)">%s</g>' %
                 lotus_solid().split("\n", 1)[1].rsplit("\n", 1)[0].rsplit("</svg>", 1)[0])
    for x in (250, 350):
        parts.append(poly(diamond(x, 30, 5)))
    for x in (28, 572):
        parts.append('<circle cx="%d" cy="30" r="3.4" fill="currentColor"/>' % x)
    return svg((600, 64), "\n".join(parts))

def divider_diamond():
    parts = ['<path d="M10,16 H262 M338,16 H590" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
             poly(diamond(300, 16, 11)), poly(diamond(272, 16, 4)), poly(diamond(328, 16, 4)),
             '<path d="M300,5 L300,27 M289,16 H311" stroke="#AA0000" stroke-width="0"/>']
    return svg((600, 32), "\n".join(parts))

def divider_wave():
    d = "M0,16 " + " ".join("q 25,-16 50,0 t 50,0" for _ in range(1)) 
    seg = "M0,16 " + " ".join("q12.5,-14 25,0 t25,0" for _ in range(12))
    return svg((600, 32), '<path d="%s" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>' % seg)

def frame_a5():
    """Double-line frame with notched corners and edge diamonds, aspect 1000 x 1414."""
    W, H, m, n = 1000, 1414, 18, 46
    def notched(m, n):
        return ("M%d,%d H%d L%d,%d V%d L%d,%d H%d L%d,%d V%d L%d,%d H%d L%d,%d V%d Z" %
                (m + n, m, W - m - n, W - m, m + n, H - m - n, W - m - n, H - m, m + n, m, H - m - n, m + n, m + n, m, m + n, m, m + n, m + n, m + n))
    def box(m, n):
        a, b, c, d = m, m, W - m, H - m
        return ("M%d,%d H%d Q%d,%d %d,%d V%d Q%d,%d %d,%d H%d Q%d,%d %d,%d V%d Q%d,%d %d,%d Z" %
                (a + n, b, c - n, c - n, b + n * 0 + n, c, b + n, d - n, c, d - n * 0, c - n, d, a + n, a + n, d - n, a, d - n, b + n, a + n, b + n, a + n, b))
    # simple, reliable: outer rect, inner rect with concave notched corners
    parts = ['<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="currentColor" stroke-width="5"/>' % (m, m, W - 2 * m, H - 2 * m)]
    i = 36
    def inner():
        a, b, c, d, r = i, i, W - i, H - i, 34
        return ("M%d,%d H%d A%d,%d 0 0 0 %d,%d V%d A%d,%d 0 0 0 %d,%d H%d A%d,%d 0 0 0 %d,%d V%d A%d,%d 0 0 0 %d,%d Z" %
                (a + r, b, c - r, r, r, c, b + r, d - r, r, r, c - r, d, a + r, r, r, a, d - r, b + r, r, r, a + r, b))
    parts.append('<path d="%s" fill="none" stroke="currentColor" stroke-width="2.4"/>' % inner())
    for x, y in [(W / 2, m), (W / 2, H - m), (m, H / 2), (W - m, H / 2)]:
        parts.append(poly(diamond(x, y, 11)))
    return svg((W, H), "\n".join(parts))

def arch_pointed():
    """Stepped pointed (ogee) arch niche - three nested outlines, 800 x 1100."""
    parts = []
    for k, sw in enumerate((6, 3.5, 2.2)):
        i = k * 34
        d = ("M%d,1100 V%d C%d,%d %d,%d 400,%d C%d,%d %d,%d %d,%d V1100" %
             (i, 520 - i * 0.3, i, 360 - i * 0.2, 262 + i * 0.5, 262 - i * 0.2 + 10, 20 + i * 1.6,
              538 - i * 0.5, 262 - i * 0.2 + 10, 800 - i, 360 - i * 0.2, 800 - i, 520 - i * 0.3))
        parts.append('<path d="%s" fill="none" stroke="currentColor" stroke-width="%s" stroke-linejoin="round"/>' % (d, sw))
    parts.append(poly(diamond(400, 8, 12)))
    return svg((800, 1100), "\n".join(parts))

def prasat():
    """Stylised multi-tier temple towers (generic, not a specific monument). 1000 x 320, solid silhouette."""
    def tower(cx, base, hgt, tiers, wbase):
        out = []
        th = hgt / (tiers + 1.8)
        for t in range(tiers):
            w = wbase * (1 - t / (tiers + 0.6))
            y1 = base - t * th
            out.append([(cx - w / 2, y1), (cx + w / 2, y1), (cx + w / 2 - 6, y1 - th), (cx - w / 2 + 6, y1 - th)])
            ww = w * 0.86
            out.append([(cx - ww / 2, y1 - th), (cx + ww / 2, y1 - th), (cx + ww / 2 - 4, y1 - th - 8), (cx - ww / 2 + 4, y1 - th - 8)])
        top = base - tiers * th
        spire = curve((cx, top), -90, hgt * 0.5, 0, 0)
        out.append(taper(spire, wbase / (tiers + 2.4), 0.6, 1.1))
        return out
    parts = []
    shapes = []
    shapes += tower(500, 300, 250, 5, 190)
    shapes += tower(330, 300, 168, 4, 128)
    shapes += tower(670, 300, 168, 4, 128)
    shapes += tower(190, 300, 100, 3, 92)
    shapes += tower(810, 300, 100, 3, 92)
    for s in shapes:
        parts.append(poly(s))
    parts.append('<rect x="40" y="296" width="920" height="22" fill="currentColor"/>')
    parts.append('<rect x="90" y="272" width="820" height="26" fill="currentColor" opacity="0.9"/>')
    return svg((1000, 320), "\n".join(parts))

def sun_medallion():
    parts = []
    cx = cy = 300
    for i in range(36):
        a = i * 10
        long = i % 2 == 0
        r0, r1 = 150, (285 if long else 232)
        tip = (cx + r1 * math.cos(math.radians(a)), cy + r1 * math.sin(math.radians(a)))
        l = (cx + r0 * math.cos(math.radians(a - 3.4)), cy + r0 * math.sin(math.radians(a - 3.4)))
        r = (cx + r0 * math.cos(math.radians(a + 3.4)), cy + r0 * math.sin(math.radians(a + 3.4)))
        parts.append(poly([l, tip, r]))
    parts.append('<circle cx="300" cy="300" r="142" fill="none" stroke="currentColor" stroke-width="4"/>')
    parts.append('<circle cx="300" cy="300" r="128" fill="none" stroke="currentColor" stroke-width="1.8"/>')
    for i in range(12):
        parts.append('<path transform="translate(300,300) rotate(%d) translate(0,-60)" d="%s" fill="currentColor" fill-rule="evenodd"/>' % (i * 30, petal(66, 17, 0.45)))
    parts.append('<circle cx="300" cy="300" r="18" fill="currentColor"/>')
    return svg((600, 600), "\n".join(parts))


def wave_border():
    seg = "M0,40 " + " ".join("q18,-34 36,0 t36,0" for _ in range(17))
    seg2 = "M0,62 " + " ".join("q18,-28 36,0 t36,0" for _ in range(17))
    return svg((1224, 80), '<path d="%s" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round"/><path d="%s" fill="none" stroke="currentColor" stroke-width="3" opacity="0.6" stroke-linecap="round"/>' % (seg, seg2))

def boat():
    parts = ['<path d="M20,120 C120,150 680,150 780,120 C770,138 700,170 400,172 C100,170 30,138 20,120Z" fill="currentColor"/>']
    parts.append(poly(taper(curve((20, 120), -125, 74, 36, 120), 7, 1)))
    parts.append(poly(taper(curve((780, 120), -55, 74, -36, -120), 7, 1)))
    for i in range(15):
        x = 70 + i * 47
        parts.append('<circle cx="%d" cy="82" r="8" fill="currentColor"/>' % x)
        parts.append('<path d="M%d,92 v28" stroke="currentColor" stroke-width="9" stroke-linecap="round"/>' % x)
        parts.append('<path d="M%d,100 L%d,150" stroke="currentColor" stroke-width="3"/>' % (x + 4, x + 24))
    return svg((800, 190), "\n".join(parts))

def krathong():
    """Floating lotus vessel with a candle (Water Festival / Pchum Ben)."""
    parts = ['<g transform="translate(150,160)">']
    for ang, h, w in [(-72, 60, 22), (72, 60, 22), (-50, 76, 22), (50, 76, 22), (-28, 88, 22), (28, 88, 22), (0, 96, 23)]:
        parts.append('<path transform="rotate(%s)" d="%s" fill="currentColor" fill-rule="evenodd"/>' % (ang, petal(h, w, 0.5)))
    parts.append('</g>')
    parts.append('<rect x="144" y="30" width="12" height="70" rx="3" fill="currentColor"/>')
    parts.append('<path d="M150,4 C162,18 162,30 150,34 C138,30 138,18 150,4Z" fill="currentColor"/>')
    parts.append('<path d="M20,170 C60,196 240,196 280,170 L262,186 C220,204 80,204 38,186Z" fill="currentColor"/>')
    return svg((300, 210), "\n".join(parts))

def candle():
    return svg((120, 300), '<path d="M60,10 C80,40 80,60 60,72 C40,60 40,40 60,10Z" fill="currentColor"/>'
               '<rect x="52" y="76" width="16" height="12" rx="3" fill="currentColor"/>'
               '<rect x="30" y="92" width="60" height="150" rx="6" fill="currentColor"/>'
               '<path d="M14,246 H106 L96,276 H24Z" fill="currentColor"/>'
               '<rect x="6" y="276" width="108" height="14" rx="5" fill="currentColor"/>')

def champei():
    parts = []
    for i in range(5):
        parts.append('<path transform="translate(80,80) rotate(%d)" d="M0,0 C26,-20 38,-52 12,-72 C-4,-62 -18,-34 0,0Z" fill="currentColor" fill-rule="evenodd" opacity="%s"/>' % (i * 72, "0.92" if i % 2 == 0 else "0.78"))
    parts.append('<circle cx="80" cy="80" r="7" fill="none" stroke="currentColor" stroke-width="0"/>')
    return svg((160, 160), "\n".join(parts))


def starburst():
    parts = []
    for i in range(24):
        a = i * 15
        r0, r1 = 40, (150 if i % 2 == 0 else 110)
        parts.append('<path d="M%s,%s L%s,%s" stroke="currentColor" stroke-width="%s" stroke-linecap="round"/>' % (
            f(160 + r0 * math.cos(math.radians(a))), f(160 + r0 * math.sin(math.radians(a))),
            f(160 + r1 * math.cos(math.radians(a))), f(160 + r1 * math.sin(math.radians(a))), "3.4" if i % 2 == 0 else "2"))
    parts.append(poly(diamond(160, 160, 16)))
    for k in range(8):
        a = k * 45 + 22.5
        parts.append('<circle cx="%s" cy="%s" r="4" fill="currentColor"/>' % (f(160 + 156 * math.cos(math.radians(a))), f(160 + 156 * math.sin(math.radians(a)))))
    return svg((320, 320), "\n".join(parts))

def ribbon():
    return svg((800, 150), '<path d="M120,20 H680 V110 H120Z" fill="currentColor"/>'
               '<path d="M120,40 L10,40 L52,75 L10,110 L120,110Z" fill="currentColor" opacity="0.78"/>'
               '<path d="M680,40 L790,40 L748,75 L790,110 L680,110Z" fill="currentColor" opacity="0.78"/>'
               '<path d="M120,110 V132 L168,110Z M680,110 V132 L632,110Z" fill="currentColor" opacity="0.55"/>')

def lattice_tile():
    return svg((80, 80), '<path d="M40,2 L78,40 L40,78 L2,40Z" fill="none" stroke="currentColor" stroke-width="2.2"/>'
               '<path d="M40,20 L60,40 L40,60 L20,40Z" fill="none" stroke="currentColor" stroke-width="1.6"/>'
               '<circle cx="40" cy="40" r="3.2" fill="currentColor"/>'
               '<path d="M0,0 L8,0 M0,0 L0,8 M80,0 L72,0 M80,0 L80,8 M0,80 L8,80 M0,80 L0,72 M80,80 L72,80 M80,80 L80,72" stroke="currentColor" stroke-width="2"/>')

def corner_simple():
    return svg((160, 160), '<path d="M6,6 H120 M6,6 V120" stroke="currentColor" stroke-width="3" fill="none"/>'
               + poly(diamond(36, 36, 9)) + '<path d="M6,26 H20 M26,6 V20" stroke="currentColor" stroke-width="0"/>')

def graduation_cap():
    return svg((300, 220), '<path d="M150,20 L290,80 L150,140 L10,80Z" fill="currentColor"/>'
               '<path d="M70,112 V170 C70,196 230,196 230,170 V112 L150,146Z" fill="currentColor" opacity="0.85"/>'
               '<path d="M270,90 V160" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>'
               '<circle cx="270" cy="172" r="12" fill="currentColor"/>')

def bbox_svg(polys_and_extra, pad=8):
    """Build an svg whose viewBox hugs the given polygons (lists of points) plus raw extra markup."""
    allp = [p for poly_ in polys_and_extra[0] for p in poly_]
    xs, ys = [p[0] for p in allp], [p[1] for p in allp]
    x0, y0, x1, y1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    body = "\n".join(poly(p_) for p_ in polys_and_extra[0]) + polys_and_extra[1]
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s %s %s %s">\n%s\n</svg>\n'
            % (f(x0), f(y0), f(x1 - x0), f(y1 - y0), body))

def volute(start, center, r0, turns, direction):
    """Centre line: eases from `start` into an inward spiral around `center`."""
    a0 = math.atan2(start[1] - center[1], start[0] - center[0])
    line = []
    for i in range(70):
        t = i / 69
        a = a0 + direction * turns * 2 * math.pi * t
        r = r0 * (1 - t) ** 1.05 + 4
        line.append((center[0] + r * math.cos(a), center[1] + r * math.sin(a)))
    return line

def kbach_corner():
    """Corner flourish (corner at top-left): a scroll along each edge, a short diagonal flame leaf, bead, diamonds."""
    o = (34, 34)
    polys = []
    for mirror in (False, True):
        c = (118, 72)
        start = (c[0], c[1] - 40)
        spiral = volute(start, c, 40, 1.25, 1)
        stem = [(o[0] + (start[0] - o[0]) * (i / 23), o[1] + (start[1] - o[1]) * (i / 23) ** 2.2) for i in range(24)]
        pts_ = taper(stem + spiral[1:], 7.5, 1.2, 0.7)
        polys.append([(y, x) for x, y in pts_] if mirror else pts_)
    polys.append(taper(curve(o, 45, 130, 0, 0, 40), 9, 0.8, 0.8))
    for t in (170, 214):
        polys.append(diamond(t, 34, 6))
        polys.append(diamond(34, t, 6))
    extra = ('<circle cx="34" cy="34" r="11" fill="currentColor"/>'
             '<circle cx="34" cy="34" r="19" fill="none" stroke="currentColor" stroke-width="2.4"/>')
    return bbox_svg((polys, extra), 16)

def kbach_strip():
    """Tileable lotus-bud border strip, 1200 x 64."""
    parts = []
    for i in range(15):
        cx = i * 80 + 40
        parts.append('<path transform="translate(%d,52)" d="%s" fill="currentColor"/>' % (cx, petal(40, 11)))
        for s_ in (-1, 1):
            parts.append('<path transform="translate(%d,52) rotate(%d)" d="%s" fill="currentColor" opacity="0.85"/>' % (cx, s_ * 48, petal(28, 8)))
        parts.append(poly(diamond(cx + 40, 40, 4)))
    parts.append('<path d="M0,58 H1200" stroke="currentColor" stroke-width="3"/>')
    return svg((1200, 64), "\n".join(parts))

def palm():
    trunk = curve((100, 520), -90, 400, 9, 0)
    polys = [taper(trunk, 9, 4.5, 0.6)]
    top = trunk[-1]
    for ang, ln, bend in [(-170, 120, -34), (-150, 138, -30), (-125, 130, -24), (-98, 118, -10), (-72, 130, 24), (-48, 138, 30), (-22, 120, 34), (-200, 96, -38), (14, 96, 38)]:
        polys.append(taper(curve(top, ang, ln, bend, 0), 7, 0.5, 0.7))
    return bbox_svg((polys, '<circle cx="%s" cy="%s" r="9" fill="currentColor"/>' % (f(top[0]), f(top[1] + 6))), 12)

def leaf_sprig():
    stem = curve((20, 330), -80, 310, 38, 0)
    polys = [taper(stem, 3.2, 1.2, 1)]
    for i in range(3, 46, 5):
        x, y = stem[i]
        s_ = 1 - i / 60
        for side, ang in ((1, -40), (-1, -140)):
            pl = petal(70 * s_ + 18, 13 * s_ + 4)
            # petal() returns a path; approximate with a polygon for bbox purposes
            h_, w_ = 70 * s_ + 18, 13 * s_ + 4
            base = [(0, 0), (w_, -h_ * .3), (w_ * .8, -h_ * .7), (0, -h_), (-w_ * .8, -h_ * .7), (-w_, -h_ * .3)]
            polys.append([(x + px * math.cos(math.radians(ang + 90)) - py * math.sin(math.radians(ang + 90)),
                           y + px * math.sin(math.radians(ang + 90)) + py * math.cos(math.radians(ang + 90))) for px, py in base])
    return bbox_svg((polys, ""), 6)

# ---- multi-tone (magic recolour hexes) ----
def confetti():
    import random
    rnd = random.Random(7)
    cols = ["#AA0001", "#AA0002", "#AA0003"]
    parts = []
    for i in range(70):
        x, y = rnd.uniform(10, 790), rnd.uniform(10, 790)
        c = cols[i % 3]
        k = i % 4
        if k == 0:
            parts.append('<rect x="%s" y="%s" width="%s" height="%s" rx="2" fill="%s" transform="rotate(%d %s %s)"/>' % (f(x), f(y), 16, 8, c, rnd.randint(0, 180), f(x), f(y)))
        elif k == 1:
            parts.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(x), f(y), rnd.choice([5, 7, 9]), c))
        elif k == 2:
            parts.append(poly(rot([(x, y - 11), (x + 10, y + 8), (x - 10, y + 8)], rnd.randint(0, 120), x, y), 'fill="%s"' % c))
        else:
            parts.append('<path d="M%s,%s q8,-12 16,0 t16,0" fill="none" stroke="%s" stroke-width="4" stroke-linecap="round"/>' % (f(x), f(y), c))
    return svg((800, 800), "\n".join(parts), 'preserveAspectRatio="xMidYMid slice"')

def balloons():
    parts = []
    for cx, cy, r, c, tilt in [(110, 130, 74, "#AA0001", -8), (230, 100, 80, "#AA0002", 4), (340, 140, 70, "#AA0003", 10)]:
        parts.append('<g transform="rotate(%d %d %d)"><ellipse cx="%d" cy="%d" rx="%d" ry="%d" fill="%s"/>'
                     '<path d="M%d,%d l-9,14 h18Z" fill="%s"/><ellipse cx="%d" cy="%d" rx="%d" ry="%d" fill="#FFFFFF" opacity="0.22"/></g>'
                     % (tilt, cx, cy + r, cx, cy, r * 0.82, r, c, cx, cy + r - 2, c, cx - r * 0.3, cy - r * 0.38, r * 0.16, r * 0.3))
        parts.append('<path d="M%d,%d C%d,%d %d,%d 230,330" fill="none" stroke="%s" stroke-width="2.4" opacity="0.8"/>' % (cx, cy + r + 12, cx + 14, cy + r + 60, 250, 280, c))
    return svg((460, 340), "\n".join(parts))

def wash():
    return svg((800, 800), '<defs><radialGradient id="a"><stop offset="0" stop-color="#AA0001" stop-opacity="0.55"/><stop offset="1" stop-color="#AA0001" stop-opacity="0"/></radialGradient>'
               '<radialGradient id="b"><stop offset="0" stop-color="#AA0002" stop-opacity="0.5"/><stop offset="1" stop-color="#AA0002" stop-opacity="0"/></radialGradient></defs>'
               '<ellipse cx="260" cy="280" rx="300" ry="250" fill="url(#a)"/><ellipse cx="520" cy="400" rx="280" ry="230" fill="url(#b)"/>'
               '<ellipse cx="380" cy="560" rx="240" ry="190" fill="url(#a)" opacity="0.7"/>')

ORNAMENTS = {
    "lotus-solid": lotus_solid, "lotus-line": lotus_line, "lotus-bud": lotus_bud,
    "kbach-corner": kbach_corner, "kbach-strip": kbach_strip,
    "divider-lotus": divider_lotus, "divider-diamond": divider_diamond, "divider-wave": divider_wave,
    "frame-a5": frame_a5, "arch-pointed": arch_pointed, "prasat-skyline": prasat,
    "sun-medallion": sun_medallion, "palm-sugar": palm, "wave-border": wave_border, "boat-dragon": boat,
    "krathong-lotus": krathong, "candle": candle, "champei": champei, "leaf-sprig": leaf_sprig,
    "starburst": starburst, "ribbon-banner": ribbon, "lattice-tile": lattice_tile,
    "corner-simple": corner_simple, "graduation-cap": graduation_cap,
    "confetti": confetti, "balloons": balloons, "watercolour-wash": wash,
}
MULTITONE = {"confetti", "balloons", "watercolour-wash"}

def write_all(outdir):
    os.makedirs(outdir, exist_ok=True)
    for name, fn in ORNAMENTS.items():
        with open(os.path.join(outdir, name + ".svg"), "w", encoding="utf-8") as fh:
            fh.write(fn())
    return list(ORNAMENTS)

if __name__ == "__main__":
    import sys
    print(write_all(sys.argv[1] if len(sys.argv) > 1 else "ornaments"))

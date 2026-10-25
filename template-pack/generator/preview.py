# -*- coding: utf-8 -*-
"""Renders a template page spec to a PNG (QA only; needs Pillow + cairosvg + PACK_FONTS)."""
import io, os, re, sys
import cairosvg
from PIL import Image, ImageDraw
from engine import M, hexrgb

def col(pal, v):
    if v is None: return None
    return pal.get(v, v)

def grad(size, g, pal):
    w, h = size
    stops = [(col(pal, c), p) for c, p in g["stops"]]
    img = Image.new("RGB", (w, h))
    px = img.load()
    import math
    a = math.radians(g.get("angle", 180))
    dx, dy = math.sin(a), -math.cos(a)
    L = abs(w * dx) + abs(h * dy)
    for y in range(h):
        for x in range(w):
            t = ((x - w / 2) * dx + (y - h / 2) * dy) / L + 0.5
            t = min(1, max(0, t))
            for i in range(len(stops) - 1):
                (c0, p0), (c1, p1) = stops[i], stops[i + 1]
                if t <= p1 or i == len(stops) - 2:
                    u = 0 if p1 == p0 else min(1, max(0, (t - p0) / (p1 - p0)))
                    r0, r1 = hexrgb(c0), hexrgb(c1)
                    px[x, y] = tuple(int(r0[k] + (r1[k] - r0[k]) * u) for k in range(3))
                    break
    return img

def svg_png(path, color, recolor, pal, wpx, hpx):
    s = open(path, encoding="utf-8").read().replace("currentColor", col(pal, color) or "#000000")
    for k, hexv in (("c1", "#AA0001"), ("c2", "#AA0002"), ("c3", "#AA0003")):
        if recolor and k in recolor:
            s = s.replace(hexv, col(pal, recolor[k]))
    png = cairosvg.svg2png(bytestring=s.encode(), output_width=max(2, wpx), output_height=max(2, hpx))
    return Image.open(io.BytesIO(png)).convert("RGBA")

def paste(img, im, x, y, opacity=1):
    if opacity < 1:
        a = im.getchannel("A").point(lambda v: int(v * opacity)); im.putalpha(a)
    img.paste(im, (int(x), int(y)), im)

def render(spec, page, root, wout=600):
    pal = spec["palette"]
    cv = spec["canvas"]
    W, H = cv["w"], cv["h"]
    s = wout / W
    img = Image.new("RGBA", (wout, round(H * s)), "#ffffff")
    for L in page["layers"]:
        x, y, w, h = L["x"] / 100 * W * s, L["y"] / 100 * H * s, L["w"] / 100 * W * s, L["h"] / 100 * H * s
        op = L.get("opacity", 1)
        t = L["type"]
        if t == "bg":
            f = L["fill"]
            if isinstance(f, dict): base = grad(img.size, f["gradient"], pal).convert("RGBA")
            else: base = Image.new("RGBA", img.size, col(pal, f))
            img.paste(base, (0, 0))
        elif t == "shape":
            lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            fill = col(pal, L.get("fill")); st = col(pal, L.get("stroke")); sw = max(1, round(L.get("strokeWidth", 0) * s)) if st else 0
            if L["shape"] == "line":
                d.line([(x, y), (x + w, y)], fill=st, width=max(1, sw))
            elif L["shape"] == "ellipse":
                d.ellipse([x, y, x + w, y + h], fill=fill, outline=st, width=sw)
            else:
                r = round(L.get("radius", 0) * s)
                d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill, outline=st, width=sw)
            if op < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * op)))
            img.alpha_composite(lay)
        elif t == "svg":
            im = svg_png(os.path.join(root, L["src"]), L["color"], L.get("recolor"), pal, round(w), round(h))
            if L.get("flipX"): im = im.transpose(Image.FLIP_LEFT_RIGHT)
            if L.get("flipY"): im = im.transpose(Image.FLIP_TOP_BOTTOM)
            if L.get("rot"):
                im = im.rotate(-L["rot"], expand=True, resample=Image.BICUBIC)
                x -= (im.width - w) / 2; y -= (im.height - h) / 2
            paste(img, im, x, y, op)
        elif t == "pattern":
            tile = max(8, round(L["tile"] * s))
            im = svg_png(os.path.join(root, L["src"]), L["color"], None, pal, tile, tile)
            lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            for yy in range(0, img.height, tile):
                for xx in range(0, img.width, tile): lay.paste(im, (xx, yy), im)
            lay.putalpha(lay.getchannel("A").point(lambda v: int(v * op)))
            img.alpha_composite(lay)
        elif t == "photo":
            lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            fc = "#d9d4cc"
            if L["shape"] == "ellipse": d.ellipse([x, y, x + w, y + h], fill=fc)
            elif L["shape"] == "arch":
                d.rectangle([x, y + w / 2, x + w, y + h], fill=fc); d.pieslice([x, y, x + w, y + w], 180, 360, fill=fc)
            else: d.rectangle([x, y, x + w, y + h], fill=fc)
            d.line([(x + w * .3, y + h * .65), (x + w * .5, y + h * .4), (x + w * .7, y + h * .65)], fill="#b9b2a7", width=max(2, round(6 * s)))
            img.alpha_composite(lay)
        elif t == "text":
            txt = L.get("literal") or spec["_copy"][L["copy"]][L["lang"]]
            if L.get("transform") == "upper": txt = txt.upper()
            size, font = L["size"] * s, L["font"]
            ft = M.font(font, size, L["weight"])
            lines = M.wrap(font, size, L["weight"], txt, w, L["letterSpacing"])
            d = ImageDraw.Draw(img)
            lh = size * L["lineHeight"]
            ls = L["letterSpacing"] * size
            lang = "km" if L["lang"] == "km" else "en"
            for i, ln in enumerate(lines):
                if ls > 0.5:
                    tw = sum(ft.getlength(c) + ls for c in ln) - ls
                else:
                    tw = ft.getlength(ln, language=lang)
                    tw = tw
                xx = x + (w - tw) / 2 if L["align"] == "center" else (x if L["align"] == "left" else x + w - tw)
                yy = y + i * lh + (lh - size) / 2 - size * 0.12
                color = col(pal, L["color"])
                if ls > 0.5:
                    cx = xx
                    for c in ln:
                        d.text((cx, yy), c, font=ft, fill=color); cx += ft.getlength(c) + ls
                else:
                    d.text((xx, yy), ln, font=ft, fill=color, language=lang)
    return img.convert("RGB")

import os, random, urllib.request
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
import config as C

INK = (25, 25, 25)
RED = (214, 39, 40)
GREEN = (118, 190, 120)
YELLOW = (255, 226, 60)
TAN = (205, 160, 90)
SKIN = (246, 222, 184)
GRAY = (150, 150, 150)

_FONTS = {
    "serif": ["/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"],
    "sans": ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "hand": [os.path.join(C.ASSETS, "PatrickHand-Regular.ttf"), "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
}


def ensure_fonts():
    p = os.path.join(C.ASSETS, "PatrickHand-Regular.ttf")
    if not os.path.exists(p):
        try:
            urllib.request.urlretrieve("https://raw.githubusercontent.com/google/fonts/main/ofl/patrickhand/PatrickHand-Regular.ttf", p)
        except Exception as ex:
            print("handwriting font download failed, using fallback:", str(ex)[:60])


@lru_cache(maxsize=128)
def font(kind, size):
    for p in _FONTS[kind]:
        if os.path.exists(p):
            return ImageFont.truetype(p, int(size))
    return ImageFont.load_default()


_DM = ImageDraw.Draw(Image.new("L", (1, 1)))


def wrap_lines(text, fnt, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if _DM.textlength(t, font=fnt) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def text_layer(text, kind, size, fill=INK, maxw=800, align="left", stroke=0, stroke_fill=(0, 0, 0), hl=None, spacing=1.18):
    f = font(kind, size)
    lines = wrap_lines(text, f, maxw)
    lh = int(size * spacing)
    pad = 10 if hl else 2
    w = int(max(_DM.textlength(l, font=f) for l in lines)) + stroke * 2 + pad * 2 + 4
    h = lh * len(lines) + stroke * 2 + pad * 2 + size // 4
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        tw = _DM.textlength(l, font=f)
        x = pad + stroke if align == "left" else (w - tw) / 2
        y = pad + stroke + i * lh
        if hl:
            d.rounded_rectangle([x - 8, y + size * 0.12, x + tw + 8, y + size * 1.08], radius=6, fill=hl)
        d.text((x, y), l, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return im


# ---------------- icons ----------------
def draw_icon(d, kind, cx, cy, r):
    P = lambda x, y: (cx + x * r, cy + y * r)
    lw = max(2, int(r * 0.07))
    fn = lambda s: font("hand", int(r * s))
    if kind == "moneybag":
        d.polygon([P(-.28, -.6), P(.28, -.6), P(.22, -.15), P(-.22, -.15)], fill=GREEN, outline=INK)
        d.ellipse([P(-.8, -.35), P(.8, 1.0)], fill=GREEN, outline=INK, width=lw)
        d.rectangle([P(-.32, -.7), P(.32, -.52)], fill=TAN, outline=INK, width=lw)
        d.text(P(0, .33), "$", font=fn(1.0), fill=INK, anchor="mm")
    elif kind == "bill":
        d.rectangle([P(-.9, -.5), P(.9, .5)], fill=GREEN, outline=INK, width=lw)
        d.ellipse([P(-.3, -.3), P(.3, .3)], outline=INK, width=lw)
        d.text(P(0, 0), "$", font=fn(.7), fill=INK, anchor="mm")
    elif kind == "briefcase":
        d.rectangle([P(-.3, -.65), P(.3, -.25)], outline=INK, width=lw)
        d.rectangle([P(-.85, -.3), P(.85, .65)], fill=TAN, outline=INK, width=lw)
        d.line([P(-.85, .1), P(.85, .1)], fill=INK, width=lw)
        d.rectangle([P(-.1, .02), P(.1, .2)], fill=YELLOW, outline=INK)
    elif kind in ("arrow_down", "arrow_up"):
        s = 1 if kind == "arrow_down" else -1
        pts = [(-.25, -.8), (.25, -.8), (.25, 0), (.6, 0), (0, .85), (-.6, 0), (-.25, 0)]
        d.polygon([P(x, y * s) for x, y in pts], fill=RED if s == 1 else GREEN, outline=INK, width=lw)
    elif kind == "bank":
        d.polygon([P(-.95, -.2), P(0, -.9), P(.95, -.2)], fill=(200, 200, 205), outline=INK)
        for i in range(4):
            x = -.7 + i * .47
            d.rectangle([P(x - .09, -.1), P(x + .09, .6)], fill=(235, 235, 240), outline=INK, width=lw)
        d.rectangle([P(-.95, .62), P(.95, .82)], fill=(200, 200, 205), outline=INK, width=lw)
    elif kind == "warning":
        d.polygon([P(0, -.9), P(.95, .75), P(-.95, .75)], fill=YELLOW, outline=INK)
        d.text(P(0, .3), "!", font=fn(1.1), fill=INK, anchor="mm")
    elif kind == "coin":
        d.ellipse([P(-.8, -.8), P(.8, .8)], fill=YELLOW, outline=INK, width=lw)
        d.ellipse([P(-.55, -.55), P(.55, .55)], outline=INK, width=max(1, lw // 2))
        d.text(P(0, 0), "$", font=fn(1.0), fill=INK, anchor="mm")
    else:  # bars
        for i, (h, c) in enumerate([(.35, (190, 190, 190)), (.7, (120, 160, 220)), (1.1, GREEN)]):
            x = -.7 + i * .5
            d.rectangle([P(x, .8 - h * 1.2), P(x + .38, .8)], fill=c, outline=INK, width=lw)
        d.line([P(-.9, .82), P(.9, .82)], fill=INK, width=lw)


@lru_cache(maxsize=64)
def icon_layer(kind, size):
    S = 3
    im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    draw_icon(ImageDraw.Draw(im), kind, size * S / 2, size * S / 2, size * S / 2 * 0.9)
    return im.resize((size, size), Image.LANCZOS)


# ---------------- stick-figure characters ----------------
ARMS = {"idle": (((165, 300), (150, 350)), ((235, 300), (250, 350))),
        "point": (((165, 300), (150, 350)), ((260, 235), (340, 200))),
        "shock": (((150, 230), (130, 170)), ((250, 230), (270, 170))),
        "sad": (((170, 310), (165, 380)), ((230, 310), (235, 380))),
        "money": (((165, 300), (150, 350)), ((255, 230), (285, 175))),
        "wave": (((165, 300), (150, 350)), ((255, 225), (290, 150)))}


@lru_cache(maxsize=600)
def character(pose="idle", mood="neutral", mouth=0, prop="", hat="", blink=0, height=500):
    S, W0, H0 = 3, 400, 640
    im = Image.new("RGBA", (W0 * S, H0 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = random.Random(3)
    P = lambda x, y: (x * S, y * S)

    def seg(a, b, w=7):
        m = ((a[0] + b[0]) / 2 + rng.uniform(-3, 3), (a[1] + b[1]) / 2 + rng.uniform(-3, 3))
        d.line([P(*a), P(*m), P(*b)], fill=INK, width=int(w * S), joint="curve")
        for p in (a, b):
            d.ellipse([P(p[0] - w / 2, p[1] - w / 2), P(p[0] + w / 2, p[1] + w / 2)], fill=INK)

    hip = (200, 410)
    seg((200, 194), hip)
    seg(hip, (158, 610))
    seg(hip, (244, 610))
    (le, lh), (re_, rh) = ARMS.get(pose, ARMS["idle"])
    seg((200, 252), le); seg(le, lh)
    seg((200, 252), re_); seg(re_, rh)
    # props
    if prop == "bag":
        draw_icon(d, "moneybag", rh[0] * S, (rh[1] - 40) * S, 50 * S)
    elif prop == "case":
        draw_icon(d, "briefcase", lh[0] * S, (lh[1] + 40) * S, 50 * S)
    elif prop == "pointer":
        d.line([P(rh[0] - 8, rh[1] + 8), P(rh[0] + 52, rh[1] - 62)], fill=(130, 85, 40), width=int(6 * S))
    elif prop == "doc":
        d.rectangle([P(lh[0] - 28, lh[1] - 5), P(lh[0] + 28, lh[1] + 62)], fill=(250, 250, 245), outline=INK, width=int(3 * S))
        for k in range(4):
            d.line([P(lh[0] - 18, lh[1] + 8 + k * 12), P(lh[0] + 18, lh[1] + 8 + k * 12)], fill=RED if k == 0 else GRAY, width=int(2 * S))
    # head
    hc, r = (200, 130), 64
    d.ellipse([P(hc[0] - r, hc[1] - r), P(hc[0] + r, hc[1] + r)], fill=SKIN, outline=INK, width=int(7 * S))
    if hat == "tophat":
        d.rectangle([P(158, 0), P(242, 66)], fill=(20, 20, 20))
        d.rectangle([P(158, 48), P(242, 62)], fill=(40, 120, 60))
        d.rounded_rectangle([P(132, 62), P(268, 82)], radius=8 * S, fill=(20, 20, 20))
    elif hat == "fedora":
        d.rounded_rectangle([P(158, 18), P(242, 70)], radius=18 * S, fill=(35, 35, 40))
        d.rectangle([P(158, 56), P(242, 66)], fill=(110, 40, 40))
        d.ellipse([P(122, 58), P(278, 86)], fill=(35, 35, 40))
    else:
        for a, b in (((170, 72), (160, 44)), ((190, 68), (188, 38)), ((212, 68), (222, 40)), ((232, 76), (248, 54))):
            seg(a, b, 6)
    ex = (176, 224)
    if blink:
        for x in ex:
            d.line([P(x - 9, 126), P(x + 9, 126)], fill=INK, width=int(5 * S))
    elif mood == "shock":
        for x in ex:
            d.ellipse([P(x - 13, 112), P(x + 13, 138)], fill=(255, 255, 255), outline=INK, width=int(4 * S))
            d.ellipse([P(x - 4, 120), P(x + 4, 130)], fill=INK)
    else:
        for x in ex:
            d.ellipse([P(x - 6, 119), P(x + 6, 131)], fill=INK)
    if hat == "fedora" or mood == "angry":
        d.line([P(158, 100), P(190, 112)], fill=INK, width=int(6 * S)); d.line([P(210, 112), P(242, 100)], fill=INK, width=int(6 * S))
    elif mood == "sad":
        d.line([P(160, 108), P(190, 97)], fill=INK, width=int(5 * S)); d.line([P(210, 97), P(240, 108)], fill=INK, width=int(5 * S))
    elif mood == "shock":
        d.line([P(160, 92), P(192, 88)], fill=INK, width=int(5 * S)); d.line([P(208, 88), P(240, 92)], fill=INK, width=int(5 * S))
    w5 = int(5 * S)
    if mood == "shock":
        d.ellipse([P(186, 148), P(214, 182)], fill=(60, 20, 20), outline=INK, width=w5)
    elif mood == "happy":
        if mouth:
            d.pieslice([P(172, 126), P(228, 178)], 10, 170, fill=(60, 20, 20), outline=INK, width=w5)
        else:
            d.arc([P(176, 128), P(224, 176)], 20, 160, fill=INK, width=w5)
    elif mood in ("sad", "angry"):
        if mouth:
            d.ellipse([P(189, 156), P(211, 180)], fill=(60, 20, 20), outline=INK, width=w5)
        else:
            d.arc([P(180, 160), P(220, 196)], 200, 340, fill=INK, width=w5)
    else:
        if mouth:
            d.ellipse([P(188, 148), P(212, 172)], fill=(60, 20, 20), outline=INK, width=w5)
        else:
            d.line([P(186, 158), P(214, 158)], fill=INK, width=w5)
    w = int(W0 * height / H0)
    return im.resize((w, height), Image.LANCZOS)


# ---------------- charts ----------------
def chart_layer(pts, size, title, fmt):
    W, H = size
    S = 2
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((int(W * .02) * S, 0), title, font=font("sans", int(H * .07) * S), fill=(70, 70, 70))
    top, bottom, left, right = int(H * .27) * S, int(H * .9) * S, int(W * .03) * S, int(W * .92) * S
    vals = [v for _, v in pts]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    n = len(pts)
    xy = [(left + (right - left) * i / (n - 1), bottom - (bottom - top) * (v - lo) / span) for i, (_, v) in enumerate(pts)]
    for g in range(5):
        y = top + (bottom - top) * g / 4
        d.line([(left, y), (right, y)], fill=(228, 228, 228), width=2 * S)
    lw = max(3, int(H * .012)) * S
    sp = int(n * .88)
    d.line(xy[:sp + 1], fill=GRAY, width=lw, joint="curve")
    d.line(xy[sp:], fill=RED, width=lw + S, joint="curve")
    w, used = max(2, n // 12), []
    cand = sorted(range(w, int(n * .93)), key=lambda i: -vals[i])
    for i in cand:
        if len(used) >= 3:
            break
        if vals[i] == max(vals[max(0, i - w):i + w + 1]) and all(abs(i - j) > n * .08 for j in used):
            used.append(i)
            d.text((xy[i][0], xy[i][1] - 14 * S), pts[i][0][:4], font=font("hand", int(H * .075) * S), fill=(95, 95, 95), anchor="ms")
    ex, ey = xy[-1]
    d.text((min(ex, right), max(ey - 22 * S, top - 10 * S)), pts[-1][0][:4], font=font("serif", int(H * .1) * S), fill=RED, anchor="ms")
    d.text((right, bottom + 4 * S), fmt.format(vals[-1]), font=font("sans", int(H * .06) * S), fill=RED, anchor="ra")
    return im.resize((W, H), Image.LANCZOS), [(x / S, y / S) for x, y in xy]


# ---------------- cards ----------------
def headline_card(title, source, ago, width):
    pad = 26
    f1, f2, f3 = font("sans", 22), font("sans", 34), font("sans", 20)
    lines = wrap_lines(title, f2, width - pad * 2)[:4]
    h = pad * 2 + 34 + len(lines) * 44 + 34
    im = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, width - 1, h - 1], radius=16, fill=(32, 33, 36), outline=(70, 72, 76), width=2)
    d.rectangle([pad, pad + 4, pad + 18, pad + 22], fill=(138, 180, 248))
    d.text((pad + 30, pad), source[:40], font=f1, fill=(190, 192, 196))
    for i, l in enumerate(lines):
        d.text((pad, pad + 40 + i * 44), l, font=f2, fill=(240, 240, 240))
    d.text((pad, h - pad - 22), ago, font=f3, fill=(150, 152, 156))
    return im


def stat_layer(value, caption, width):
    big = text_layer(value, "serif", int(width * .2), fill=RED, maxw=width)
    cap = text_layer(caption, "hand", int(width * .075), maxw=width, align="center")
    w = max(big.width, cap.width)
    im = Image.new("RGBA", (w, big.height + cap.height + 6), (0, 0, 0, 0))
    im.paste(big, ((w - big.width) // 2, 0), big)
    im.paste(cap, ((w - cap.width) // 2, big.height + 6), cap)
    return im


def banner_layer(text, size):
    t = text_layer(text, "sans", size, fill=(255, 255, 255), maxw=900)
    im = Image.new("RGBA", (t.width + 60, t.height + 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, im.height], fill=(20, 20, 20, 235))
    d.rectangle([0, 0, 12, im.height], fill=YELLOW)
    im.paste(t, (30, 4), t)
    return im

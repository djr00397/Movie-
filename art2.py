"""Doodle building blocks in the style of explainer videos: speech bubbles, chalkboard, newspaper, object mascots with eyes,
hand-drawn circles/arrows, photo cards. All drawn from scratch (original artwork)."""
import math, random
from PIL import Image, ImageDraw, ImageChops
import art
from art import font, text_layer, INK, RED, GREEN, YELLOW, TAN, wrap_lines

BOARD = (44, 112, 62)
FRAME = (112, 74, 44)


def _ss(w, h, fn, S=3):
    im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    fn(ImageDraw.Draw(im), S)
    return im.resize((w, h), Image.LANCZOS)


def handwritten(text, size, maxw=600, fill=INK, align="left"):
    return text_layer(text, "hand", size, fill=fill, maxw=maxw, align=align)


def bubble(text, size=40, maxw=420, tail="left"):
    t = text_layer(text, "hand", size, maxw=maxw, align="center")
    pad = int(size * .7)
    w, h = t.width + pad * 2, t.height + pad * 2
    H = h + int(size * .9)
    def fn(d, S):
        d.ellipse([3 * S, 3 * S, (w - 3) * S, (h - 3) * S], fill=(255, 255, 255), outline=INK, width=4 * S)
        x0 = int(w * .22) if tail == "left" else int(w * .78)
        sg = 1 if tail == "left" else -1
        d.polygon([(x0 * S, (h - 8) * S), ((x0 + sg * 8) * S, (H - 2) * S), ((x0 + sg * 44) * S, (h - 16) * S)], fill=(255, 255, 255), outline=INK)
        d.polygon([((x0 + sg * 2) * S, (h - 10) * S), ((x0 + sg * 40) * S, (h - 18) * S), ((x0 + sg * 8) * S, (H - 6) * S)], fill=(255, 255, 255))
    im = _ss(w, H, fn)
    im.paste(t, (pad, pad), t)
    return im


def board(text, w, h):
    def fn(d, S):
        d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=10 * S, fill=FRAME, outline=INK, width=4 * S)
        d.rectangle([22 * S, 22 * S, (w - 22) * S, (h - 22) * S], fill=BOARD, outline=(30, 70, 40), width=3 * S)
    im = _ss(w, h, fn)
    t = text_layer(text, "hand", int(h * .22), fill=(250, 250, 244), maxw=int(w * .72), align="center")
    sc = min(1.0, (w * .8) / t.width, (h * .62) / t.height)
    if sc < 1:
        t = t.resize((int(t.width * sc), int(t.height * sc)), Image.LANCZOS)
    im.paste(t, ((w - t.width) // 2, (h - t.height) // 2), t)
    return im


def newspaper(label, w):
    h = int(w * .72)
    def fn(d, S):
        d.polygon([(0, 14 * S), (w * S, 0), ((w - 6) * S, h * S), (6 * S, (h - 8) * S)], fill=(236, 230, 214), outline=INK)
        d.line([(0, 14 * S), (w * S, 0), ((w - 6) * S, h * S), (6 * S, (h - 8) * S), (0, 14 * S)], fill=INK, width=4 * S)
        rng = random.Random(5)
        for r in range(7):
            y = (int(h * .5) + r * int(h * .06)) * S
            d.line([(int(w * .08) * S, y), (int(w * (.45 if r % 3 == 0 else .92)) * S, y + rng.randint(-2, 2) * S)], fill=(150, 144, 130), width=3 * S)
        d.rectangle([int(w * .06) * S, int(h * .45) * S, int(w * .36) * S, int(h * .85) * S], outline=(150, 144, 130), width=2 * S)
    im = _ss(w, h, fn)
    t = text_layer(label, "sans", int(w * .1), maxw=int(w * .9), align="center")
    sc = min(1.0, w * .86 / t.width)
    t = t.resize((int(t.width * sc), int(t.height * sc)), Image.LANCZOS)
    im.paste(t, ((w - t.width) // 2, int(h * .12)), t)
    return im


def _eyes(d, S, cx, cy, gap, r):
    for sg in (-1, 1):
        x = cx + sg * gap
        d.ellipse([(x - r) * S, (cy - r * 1.2) * S, (x + r) * S, (cy + r * 1.2) * S], fill=(255, 255, 255), outline=INK, width=max(2, int(r * .22 * S)))
        d.ellipse([(x - r * .3 + sg * r * .1) * S, (cy - r * .1) * S, (x + r * .45 + sg * r * .1) * S, (cy + r * .7) * S], fill=INK)


def mascot(kind, size):
    """Object character: a thing with cartoon eyes and little legs (earth, bank, money bag, AI chip, house, oil barrel, coin, chart)."""
    W, H = size, int(size * 1.25)
    def fn(d, S):
        cx, cy, r = W / 2, size * .46, size * .4
        lw = max(3, int(size * .025)) * S
        if kind == "earth":
            d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=(70, 140, 220), outline=INK, width=lw)
            rng = random.Random(2)
            for _ in range(4):
                x, y = cx + rng.uniform(-.5, .4) * r, cy + rng.uniform(-.6, .4) * r
                d.ellipse([x * S, y * S, (x + r * .55) * S, (y + r * .38) * S], fill=(96, 176, 96), outline=INK, width=lw // 2)
            ey = cy
        elif kind == "chip":
            d.rounded_rectangle([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], radius=int(r * .2) * S, fill=(34, 40, 52), outline=INK, width=lw)
            for i in range(5):
                p = (cx - r * .7 + i * r * .35) * S
                d.line([(p, (cy - r) * S), (p, (cy - r * 1.25) * S)], fill=(180, 180, 190), width=lw)
                d.line([(p, (cy + r) * S), (p, (cy + r * 1.25) * S)], fill=(180, 180, 190), width=lw)
            d.text((cx * S, (cy - r * .5) * S), "AI", font=font("sans", int(r * .5) * S), fill=(120, 220, 255), anchor="mm")
            ey = cy + r * .2
        elif kind == "house":
            d.polygon([((cx - r * 1.1) * S, (cy - r * .1) * S), (cx * S, (cy - r * 1.05) * S), ((cx + r * 1.1) * S, (cy - r * .1) * S)], fill=(190, 70, 60), outline=INK, width=lw)
            d.rectangle([(cx - r * .85) * S, (cy - r * .1) * S, (cx + r * .85) * S, (cy + r * .9) * S], fill=(240, 220, 170), outline=INK, width=lw)
            ey = cy + r * .25
        elif kind == "barrel":
            d.rounded_rectangle([(cx - r * .8) * S, (cy - r) * S, (cx + r * .8) * S, (cy + r) * S], radius=int(r * .3) * S, fill=(60, 60, 70), outline=INK, width=lw)
            for yy in (-.55, .55):
                d.line([((cx - r * .8) * S, (cy + yy * r) * S), ((cx + r * .8) * S, (cy + yy * r) * S)], fill=(210, 170, 40), width=lw)
            ey = cy
        elif kind == "bank":
            art.draw_icon(d, "bank", cx * S, cy * S, r * S * 1.1)
            ey = cy + r * .05
        elif kind == "coin":
            art.draw_icon(d, "coin", cx * S, cy * S, r * S * 1.15)
            ey = cy - r * .1
        elif kind == "chart":
            art.draw_icon(d, "bars", cx * S, cy * S, r * S * 1.15)
            ey = cy - r * .5
        else:
            art.draw_icon(d, "moneybag", cx * S, cy * S, r * S * 1.05)
            ey = cy - r * .12
        _eyes(d, S, cx, ey - r * .12, r * .3, r * .17)
        for sx in (-.3, .3):
            x = cx + sx * r
            d.line([(x * S, (cy + r * 1.0) * S), ((x + sx * 15) * S, (H - 12) * S)], fill=INK, width=lw)
            d.ellipse([(x + sx * 15 - 14) * S, (H - 20) * S, (x + sx * 15 + 14) * S, (H - 4) * S], fill=INK)
    return _ss(W, H, fn)


def red_circle(w, h, thick=7):
    def fn(d, S):
        d.ellipse([thick * S, thick * S, (w - thick) * S, (h - thick) * S], outline=RED, width=thick * S)
    return _ss(w, h, fn)


def trend_arrow(w, h, up=True, color=None):
    col = color or (GREEN if up else RED)
    def fn(d, S):
        pts = [(.04, .88), (.28, .6), (.42, .72), (.7, .32), (.9, .12)] if up else [(.04, .12), (.28, .4), (.42, .28), (.7, .68), (.9, .88)]
        P = [(x * w * S, y * h * S) for x, y in pts]
        d.line(P, fill=col, width=int(min(w, h) * .07 * S), joint="curve")
        ex, ey = P[-1]
        ang = math.atan2(P[-1][1] - P[-2][1], P[-1][0] - P[-2][0])
        L = min(w, h) * .26 * S
        d.polygon([(ex + math.cos(ang) * L * .5, ey + math.sin(ang) * L * .5),
                   (ex + math.cos(ang + 2.5) * L, ey + math.sin(ang + 2.5) * L),
                   (ex + math.cos(ang - 2.5) * L, ey + math.sin(ang - 2.5) * L)], fill=col)
    return _ss(w, h, fn)


def cycle_arrows(size):
    def fn(d, S):
        c, r = size / 2 * S, size * .36 * S
        lw = int(size * .06 * S)
        for a0 in (20, 200):
            d.arc([c - r, c - r, c + r, c + r], a0, a0 + 140, fill=RED, width=lw)
            a = math.radians(a0 + 140)
            ex, ey = c + r * math.cos(a), c + r * math.sin(a)
            tg = a + math.pi / 2
            L = size * .12 * S
            d.polygon([(ex + math.cos(tg) * L, ey + math.sin(tg) * L), (ex + math.cos(tg + 2.4) * L, ey + math.sin(tg + 2.4) * L),
                       (ex + math.cos(tg - 2.4) * L, ey + math.sin(tg - 2.4) * L)], fill=RED)
    return _ss(size, size, fn)


def cross_out(size):
    def fn(d, S):
        w = int(size * .06 * S)
        d.line([(.08 * size * S, .08 * size * S), (.92 * size * S, .92 * size * S)], fill=RED, width=w)
        d.line([(.92 * size * S, .08 * size * S), (.08 * size * S, .92 * size * S)], fill=RED, width=w)
    return _ss(size, size, fn)


def photo_card(photo, w, tilt=-3):
    ph = photo.convert("RGB")
    sc = (w - 28) / ph.width
    ph = ph.resize((w - 28, max(40, int(ph.height * sc))), Image.LANCZOS)
    h = ph.height + 28
    im = Image.new("RGBA", (w, h + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 10, w - 1, h + 9], fill=(255, 255, 255), outline=INK, width=3)
    im.paste(ph, (14, 24))
    d.rectangle([w // 2 - 40, 0, w // 2 + 40, 22], fill=(240, 224, 150, 210))
    return im.rotate(tilt, resample=Image.BICUBIC, expand=True)


def podium(w):
    h = int(w * .5)
    def fn(d, S):
        d.polygon([(.06 * w * S, 0), (.94 * w * S, 0), (w * S, h * S), (0, h * S)], fill=(112, 74, 44), outline=INK)
        d.line([(.06 * w * S, 0), (.94 * w * S, 0), (w * S, h * S), (0, h * S), (.06 * w * S, 0)], fill=INK, width=4 * S)
        d.rectangle([.3 * w * S, .25 * h * S, .7 * w * S, .6 * h * S], outline=(236, 200, 120), width=3 * S)
    return _ss(w, h, fn)


def flag(w):
    h = int(w * .62)
    def fn(d, S):
        for i in range(7):
            d.rectangle([0, i * h / 7 * S, w * S, (i + 1) * h / 7 * S], fill=(200, 40, 50) if i % 2 == 0 else (250, 250, 250))
        d.rectangle([0, 0, w * .45 * S, h * 4 / 7 * S], fill=(40, 60, 120))
        for r in range(3):
            for c in range(4):
                d.ellipse([(w * (.05 + c * .1)) * S, (h * (.07 + r * .15)) * S, (w * (.05 + c * .1) + 7) * S, (h * (.07 + r * .15) + 7) * S], fill="white")
        d.rectangle([0, 0, w * S - 1, h * S - 1], outline=INK, width=4 * S)
    return _ss(w, h, fn)


def reveal_x(im, f):
    w = max(2, int(im.width * max(0.0, min(1.0, f))))
    return im.crop((0, 0, w, im.height)), w


def reveal_wedge(im, f):
    """Draw-on effect for circles/cycles: reveal clockwise from the top."""
    f = max(0.0, min(1.0, f))
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).pieslice([-im.width, -im.height, 2 * im.width, 2 * im.height], -90, -90 + 360 * f, fill=255)
    out = im.copy()
    out.putalpha(ImageChops.multiply(im.getchannel("A"), m))
    return out

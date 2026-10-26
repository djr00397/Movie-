"""News-evidence graphics: documentary-style newspaper page with animated highlighter, TV news screen, 'verified' stamp,
scrolling ticker, data-source tag. Headlines/snippets come from the real RSS evidence of the video's topic."""
import random, re
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import art
from art import font, wrap_lines, INK, RED, YELLOW

MARKERS = [(190, 245, 60), (255, 120, 220), (255, 226, 60), (90, 230, 215)]
_DM = ImageDraw.Draw(Image.new("L", (1, 1)))


@lru_cache(maxsize=4)
def paper_texture(w, h):
    rng = np.random.default_rng(4)
    n = rng.normal(0, 1, (h // 3 + 1, w // 3 + 1))
    n = np.kron(n, np.ones((3, 3)))[:h, :w]
    base = np.full((h, w, 3), (243, 238, 224), dtype=np.float32) + n[..., None] * 3.0
    yy, xx = np.mgrid[0:h, 0:w]
    vig = 1 - 0.10 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    base *= vig[..., None]
    return Image.fromarray(np.clip(base, 0, 255).astype("uint8"), "RGB")


def _find_box(lines_pos, words, font_):
    """bbox of the first occurrence of `words` inside wrapped lines -> (x0,y0,x1,y1)"""
    for (x, y, text, lh) in lines_pos:
        j = text.lower().find(words.lower())
        if j >= 0:
            x0 = x + _DM.textlength(text[:j], font=font_)
            return (x0, y, x0 + _DM.textlength(text[j:j + len(words)], font=font_), y + lh)
    return None


def paper_page(outlet, date_txt, headline, snippet, hl_words, w, h, marker=0):
    """Returns (page RGBA, highlight RGBA, highlight box in page coords)."""
    page = paper_texture(w, h).copy().convert("RGBA")
    d = ImageDraw.Draw(page)
    pad = int(w * .05)
    # masthead
    mf = font("serif", int(h * .085))
    name = outlet[:34]
    while _DM.textlength(name, font=mf) > w - 2 * pad - 140 and len(name) > 6:
        name = name[:-2]
    d.text((pad, int(h * .035)), name, font=mf, fill=(25, 25, 25))
    d.line([(pad, int(h * .135)), (w - pad, int(h * .135))], fill=(25, 25, 25), width=4)
    d.line([(pad, int(h * .145)), (w - pad, int(h * .145))], fill=(25, 25, 25), width=1)
    d.text((pad, int(h * .155)), date_txt.upper(), font=font("sans", int(h * .030)), fill=(90, 86, 78))
    d.rectangle([w - pad - 130, int(h * .04), w - pad, int(h * .10)], fill=(232, 112, 36))
    d.text((w - pad - 65, int(h * .07)), "TODAY", font=font("sans", int(h * .036)), fill="white", anchor="mm")
    # headline
    hf = font("serif", int(h * .088))
    hl_lines = wrap_lines(headline, hf, w - 2 * pad)[:4]
    lh = int(h * .098)
    y = int(h * .215)
    pos = []
    for l in hl_lines:
        d.text((pad, y), l, font=hf, fill=(20, 20, 20))
        pos.append((pad, y, l, lh))
        y += lh
    box = _find_box(pos, hl_words, hf) if hl_words else None
    # body: real snippet text in 2 columns, then grey filler
    bf = font("sans", int(h * .034))
    y += int(h * .03)
    colw = (w - 2 * pad - 30) // 2
    body = (snippet or "").strip()
    blines = wrap_lines(body, bf, colw)[:5] if body else []
    for i, l in enumerate(blines):
        d.text((pad, y + i * int(h * .045)), l, font=bf, fill=(60, 58, 52))
    rng = random.Random(len(headline))
    for col in (0, 1):
        for i in range(7):
            x0 = pad + col * (colw + 30)
            yy = y + (len(blines) * int(h * .045) if col == 0 else 0) + i * int(h * .045)
            if yy + 14 > h - 10:
                break
            d.line([(x0, yy + 10), (x0 + int(colw * rng.uniform(.6, 1.0)), yy + 10)], fill=(176, 170, 156), width=5)
    hl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if box:
        m = MARKERS[marker % len(MARKERS)]
        ImageDraw.Draw(hl).rounded_rectangle([box[0] - 6, box[1] + int(h * .012), box[2] + 6, box[3] - int(h * .006)], radius=8, fill=m + (150,))
        box = tuple(int(v) for v in box)
    d.rectangle([0, 0, w - 1, h - 1], outline=(150, 146, 134), width=3)
    return page, hl, box


def tv_screen(outlet, headline, w):
    """Generic TV news screen (no real logos): LIVE tag, anchor lower-third, headline."""
    h = int(w * .60)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=22, fill=(24, 24, 28), outline=INK, width=4)
    sx0, sy0, sx1, sy1 = 18, 18, w - 18, h - 38
    for i in range(sy1 - sy0):                                     # blue studio gradient
        t = i / (sy1 - sy0)
        d.line([(sx0, sy0 + i), (sx1, sy0 + i)], fill=(int(24 + 30 * t), int(60 + 50 * t), int(130 + 40 * t)))
    d.rounded_rectangle([sx0 + 16, sy0 + 14, sx0 + 120, sy0 + 52], radius=6, fill=RED)
    d.text((sx0 + 68, sy0 + 33), "LIVE", font=font("sans", 26), fill="white", anchor="mm")
    d.rectangle([sx0, sy1 - int(h * .30), sx1, sy1 - int(h * .10)], fill=(250, 250, 250))
    d.rectangle([sx0, sy1 - int(h * .30), sx0 + 14, sy1 - int(h * .10)], fill=YELLOW)
    d.rectangle([sx0, sy1 - int(h * .10), sx1, sy1], fill=(200, 30, 40))
    d.text((sx0 + 20, sy1 - int(h * .075)), outlet.upper()[:30], font=font("sans", int(h * .05)), fill="white")
    f = font("sans", int(h * .062))
    lines = wrap_lines(headline, f, sx1 - sx0 - 40)[:2]
    for i, l in enumerate(lines):
        d.text((sx0 + 26, sy1 - int(h * .285) + i * int(h * .075)), l, font=f, fill=(20, 20, 24))
    d.rectangle([w // 2 - 50, h - 30, w // 2 + 50, h - 14], fill=(60, 60, 66))
    return im


def stamp(text, w=300, color=(30, 150, 70), rot=-10):
    h = int(w * .34)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([4, 4, w - 5, h - 5], radius=14, outline=color, width=8)
    f = font("sans", int(h * .46))
    d.text((w / 2, h / 2), text, font=f, fill=color, anchor="mm")
    return im.rotate(rot, expand=True, resample=Image.BICUBIC)


def check_badge(size=64):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([2, 2, size - 3, size - 3], fill=(30, 160, 80), outline=INK, width=4)
    d.line([(size * .26, size * .52), (size * .44, size * .70), (size * .76, size * .32)], fill="white", width=int(size * .12), joint="curve")
    return im


def ticker_strip(titles, h=46):
    f = font("sans", int(h * .5))
    txt = "   \u25cf   ".join(t[:90] for t in titles if t) + "   \u25cf   "
    w = int(_DM.textlength(txt, font=f)) + 20
    im = Image.new("RGBA", (max(w, 800), h), (200, 30, 40, 255))
    d = ImageDraw.Draw(im)
    d.text((10, h * .22), txt, font=f, fill="white")
    return im


def data_tag(text, size=30):
    f = font("hand", size)
    w = int(_DM.textlength(text, font=f)) + size * 2
    im = Image.new("RGBA", (w, int(size * 1.7)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, im.height - 1], radius=int(size * .5), fill=(255, 255, 255, 235), outline=INK, width=3)
    r = size * .36
    d.ellipse([size * .45, size * .35, size * .45 + r * 2, size * .35 + r * 2], outline=INK, width=3)
    d.line([(size * .45 + r * 1.7, size * .35 + r * 1.7), (size * .45 + r * 2.6, size * .35 + r * 2.6)], fill=INK, width=4)
    d.text((size * 1.5, im.height / 2), text, font=f, fill=INK, anchor="lm")
    return im

"""Six different thumbnail designs. The design is chosen from the story itself (person / big number / chart / versus / explainer / news)
and the last designs used are remembered in history/, so consecutive videos never look the same."""
import glob, hashlib, os, re, time
from PIL import Image, ImageDraw
import config as C, art, art2, puppet as PU, video as V

W, H = 1280, 720
YEL, RED = art.YELLOW, art.RED


def _hash(s):
    return int(hashlib.md5(s.encode()).hexdigest(), 16)


def poster_text(text, w, h, fill=(255, 255, 255), stroke=9, hl=True, kind="sans", upper=True, max_size=170):
    text = text.upper() if upper else text
    for size in range(max_size, 36, -6):
        f = art.font(kind, size)
        lines = art.wrap_lines(text, f, w)
        lh = int(size * 1.08)
        if len(lines) * lh <= h and all(art._DM.textlength(l, font=f) <= w for l in lines):
            break
    im = Image.new("RGBA", (w + 40, len(lines) * lh + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    target = max(text.split(), key=len) if hl else None
    for i, l in enumerate(lines):
        y = 10 + i * lh
        if target and target in l:
            j = l.find(target)
            x0 = 20 + art._DM.textlength(l[:j], font=f)
            d.rounded_rectangle([x0 - 10, y + size * .08, x0 + art._DM.textlength(target, font=f) + 10, y + size * 1.02], radius=10, fill=YEL)
            d.text((20, y), l[:j], font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
            d.text((x0, y), target, font=f, fill=(20, 20, 20))
            rest = l[j + len(target):]
            d.text((x0 + art._DM.textlength(target, font=f), y), rest, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
        else:
            d.text((20, y), l, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))
    return im


def person(key, gesture, mood, h, prop="", mouth=1):
    pose = dict(PU.G[gesture])
    pose.update(lx=0, ly=0)
    return PU.draw(key, pose, mouth, mood, 0, prop, h)


def paste(img, layer, x, y):
    img.paste(layer, (int(x), int(y)), layer)


# ---------------------------------------------------------------- templates
def t_chart(seo, ev, ctx):
    img = Image.new("RGB", (W, H), ctx["light"])
    words = seo["thumb_text"].split()
    k = max(1, (len(words) + 1) // 2)
    a = art.text_layer(" ".join(words[:k]), "serif", 92, maxw=int(W * .46))
    paste(img, a, 50, 70)
    y = 70 + a.height
    rest = " ".join(words[k:])
    if rest:
        b = art.text_layer(rest, "serif", 108, maxw=int(W * .46))
        paste(img, b, 50, y)
        y += b.height
    ImageDraw.Draw(img).rectangle([56, y + 4, 56 + int(W * .30), y + 14], fill=RED)
    s = ev["series"].get(ev.get("main"))
    ch, _ = art.chart_layer(s["pts"], (int(W * .50), int(H * .56)), s["title"], s["fmt"])
    paste(img, ch, W * .48, H * .06)
    paste(img, person("host", "worry", "shock", 330), -40, H - 330)
    paste(img, person(ctx["pers"], "point_L", "angry", 380, "doc"), W * .70, H - 380)
    paste(img, art.icon_layer("moneybag", 150), W * .50, H - 170)
    return img


def t_persona(seo, ev, ctx):
    img = Image.new("RGB", (W, H), ctx["dark"])
    d = ImageDraw.Draw(img)
    for i in range(0, W, 60):                                   # sunburst stripes
        d.polygon([(W * .72, H * .6), (i, -20), (i + 30, -20)], fill=ctx["dark2"])
    pt = poster_text(seo["thumb_text"], int(W * .55), int(H * .66))
    paste(img, pt, 36, 60)
    pr = person(ctx["pers"], ctx["gest"], ctx["mood"], 840, "", 2)
    paste(img, pr, W - pr.width * .86, H - pr.height * .86)
    if ctx["stat"]:
        s = art.text_layer(ctx["stat"], "sans", 96, fill=(255, 255, 255), stroke=7, maxw=500)
        d.rounded_rectangle([40, H - 190, 60 + s.width + 30, H - 40], radius=24, fill=RED, outline=(0, 0, 0), width=6)
        paste(img, s, 58, H - 178)
    paste(img, art2.trend_arrow(230, 160, ctx["up"]), W * .50, H * .62)
    return img


def t_versus(seo, ev, ctx):
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.polygon([(0, 0), (W * .54, 0), (W * .46, H), (0, H)], fill=(40, 110, 220))
    d.polygon([(W * .54, 0), (W, 0), (W, H), (W * .46, H)], fill=(220, 50, 60))
    a, b = ctx["pair"]
    ma, mb = art2.mascot(a, 330), art2.mascot(b, 330)
    paste(img, ma, W * .12, H * .30)
    paste(img, mb, W * .62, H * .30)
    vs = art.text_layer("VS", "sans", 150, fill=(255, 255, 255), stroke=10)
    d.ellipse([W / 2 - 110, H * .5 - 100, W / 2 + 110, H * .5 + 120], fill=(15, 15, 20), outline=YEL, width=10)
    paste(img, vs, W / 2 - vs.width / 2, H * .5 - 85)
    pt = poster_text(seo["thumb_text"], int(W * .9), 190, hl=False, max_size=110)
    paste(img, pt, (W - pt.width) / 2, 12)
    return img


def t_board(seo, ev, ctx):
    img = Image.new("RGB", (W, H), ctx["light"])
    bd = art2.board(seo["thumb_text"], int(W * .64), int(H * .64))
    paste(img, bd, 40, 50)
    paste(img, person("host", "point_L", "happy", 650, "pointer"), W * .66, H - 650)
    tag = art.text_layer("EXPLAINED", "sans", 74, fill=(255, 255, 255), stroke=0)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, H - 150, 70 + tag.width, H - 40], radius=18, fill=RED, outline=(0, 0, 0), width=6)
    paste(img, tag, 55, H - 140)
    paste(img, art2.mascot(ctx["mk"], 220), W * .50, H * .62)
    return img


def t_breaking(seo, ev, ctx):
    img = Image.new("RGB", (W, H), ctx["light"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 150, W, H], fill=RED)
    np_ = art2.newspaper("BREAKING NEWS", int(W * .60))
    np_ = np_.rotate(4, expand=True, resample=Image.BICUBIC)
    paste(img, np_, 20, 40)
    pt = poster_text(seo["thumb_text"], int(W * .54), int(H * .34), fill=(20, 20, 20), stroke=0, hl=False, max_size=96, upper=True)
    paste(img, pt, 60, 220)
    paste(img, person("host", "shrug", "shock", 700, "", 2), W * .64, H - 700)
    sx = ctx["stat"] or "NOW"
    s = art.text_layer(sx, "sans", 96, fill=(255, 255, 255), stroke=0, maxw=700)
    paste(img, s, 50, H - 135)
    paste(img, art2.trend_arrow(200, 140, ctx["up"]), W * .50, H - 175)
    return img


def t_bigstat(seo, ev, ctx):
    img = Image.new("RGB", (W, H), ctx["dark"])
    d = ImageDraw.Draw(img)
    big = art.text_layer(ctx["stat"], "serif", 330, fill=(255, 255, 255), stroke=14, maxw=int(W * .95))
    sc = min(1.0, W * .9 / big.width, H * .55 / big.height)
    big = big.resize((int(big.width * sc), int(big.height * sc)), Image.LANCZOS)
    paste(img, big, 30, 20)
    pt = poster_text(seo["thumb_text"], int(W * .62), int(H * .34), hl=True, max_size=100)
    paste(img, pt, 30, H - pt.height - 20)
    paste(img, art2.mascot(ctx["mk"], 330), W * .70, H * .42)
    paste(img, art2.trend_arrow(250, 170, ctx["up"]), W * .66, 40)
    return img


TEMPLATES = {"chart": t_chart, "persona": t_persona, "versus": t_versus, "board": t_board, "breaking": t_breaking, "bigstat": t_bigstat}


def recent():
    out = []
    for f in sorted(glob.glob(os.path.join(C.HIST, "thumb-*.txt"))):
        try:
            out.append(open(f).read().strip())
        except Exception:
            pass
    return out[-3:]


def record(template, mode):
    open(os.path.join(C.HIST, f"thumb-{int(time.time())}-{mode}.txt"), "w").write(template)


def choose(topic, ev, seo, script):
    text = " ".join([topic["title"], seo["thumb_text"]] + [s["text"] for s in script["sections"]][:2])
    stat = V.find_stat(seo["thumb_text"] + " " + topic["title"]) or V.find_stat(text)
    pers = PU.find_persona(text)
    score = {"chart": 2 if ev["series"] else -99, "persona": 3 if pers else -99, "bigstat": 3 if stat else -99,
             "versus": 2 if re.search(r"\bvs\b|versus|against|battle|showdown|war\b", topic["title"], re.I) else -99,
             "board": 1 + (2 if topic.get("evergreen") else 0), "breaking": 1 + (1 if V.BREAKING.search(topic["title"]) else 0)}
    rec = recent()
    for back, pen in ((1, 10), (2, 4), (3, 1.5)):
        if len(rec) >= back:
            score[rec[-back]] = score.get(rec[-back], 0) - pen
    for k in score:
        score[k] += (_hash(topic["title"] + k) % 100) / 100.0           # tie-break noise
    return max(score, key=score.get), stat, pers


def make(topic, ev, seo, script, out):
    name, stat, pers = choose(topic, ev, seo, script)
    text = " ".join([topic["title"]] + [s["text"] for s in script["sections"]][:2])
    h = _hash(topic["title"])
    palettes = [((200, 30, 40), (170, 20, 32)), ((20, 60, 170), (14, 44, 130)), ((16, 20, 32), (30, 36, 56)), ((0, 120, 80), (0, 92, 62)), ((90, 30, 150), (68, 20, 118))]
    lights = [(255, 255, 255), (255, 247, 220), (226, 240, 255), (255, 235, 235)]
    dark, dark2 = palettes[h % len(palettes)]
    mood = V.mood_of(text)
    kinds = ["bank", "chip", "earth", "house", "barrel", "coin", "chart", "moneybag"]
    found = []
    for rx, k in V.MASCOTS:
        if re.search(rx, text, re.I) and k not in found:
            found.append(k)
    pair = (found + [x for x in ["bank", "chip", "earth"] if x not in found])[:2]
    ctx = dict(light=lights[(h >> 3) % len(lights)], dark=dark, dark2=dark2, stat=stat, pers=(pers or "powell") if name == "chart" else (pers or "host"),
               gest={"shock": "worry", "sad": "shrug", "happy": "cheer"}.get(mood, "palms_up"), mood={"neutral": "shock"}.get(mood, mood),
               up=mood != "shock" and mood != "sad", pair=pair, mk=(found or [kinds[h % 8]])[0])
    img = TEMPLATES[name](seo, ev, ctx).convert("RGB")
    img.save(out, "JPEG", quality=92)
    print("thumbnail template:", name)
    return out, name

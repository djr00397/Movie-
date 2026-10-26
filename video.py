import re, math, bisect, subprocess, random
import numpy as np
from PIL import Image, ImageDraw
import config as C, art, art2, puppet as PU, sources as S, media

ICONS = [(r"crash|fall|plunge|drop|collapse|tumbl|slump|sell-?off|lose|loss|decline|down", "arrow_down"),
         (r"surge|rally|rise|record|soar|jump|gain|boom|climb|up\b", "arrow_up"),
         (r"bank|fed\b|federal|reserve|central|govern", "bank"),
         (r"risk|warn|danger|fear|bubble|crisis|panic|trouble", "warning"),
         (r"profit|money|cash|dollar|wealth|billion|million|trillion|rich", "moneybag"),
         (r"bond|yield|treasur|debt|loan|credit|margin|borrow", "bill"),
         (r"compan|firm|business|ceo|job|work|layoff|worker|employ", "briefcase"),
         (r"bitcoin|crypto|coin", "coin")]
NEG = re.compile(r"crash|fall|plunge|drop|collapse|tumbl|slump|sell-?off|loss|decline|risk|fear|bubble|crisis|panic|trouble|hurt|pain|debt|danger|warn|recession|worse|trap|burst|wipe", re.I)
POS = re.compile(r"surge|rally|record|soar|jump|gain|boom|climb|profit|growth|rich|win|strong|rise|better|recover", re.I)
PHRASES = ["interest rates", "margin debt", "inflation", "recession", "stock market", "bond yields", "unemployment", "federal reserve",
           "tariffs", "the bubble", "the crash", "national debt", "housing market", "bitcoin", "oil prices", "earnings", "layoffs",
           "hedge funds", "credit", "the dollar", "gold", "supply chain", "GDP", "trade war", "private credit", "volatility"]
STAT = re.compile(r"\$\s?\d[\d,\.]*\s?(?:trillion|billion|million|thousand)?|\d[\d,\.]*\s?(?:%|percent|trillion|billion|million)")
MASCOTS = [(r"\bai\b|chip|nvidia|data cent|semiconductor|tech", "chip"), (r"housing|home|mortgage|real estate|rent", "house"),
           (r"\boil\b|energy|gas|crude|opec", "barrel"), (r"bank|fed\b|federal reserve|central bank|treasury|government|regulat", "bank"),
           (r"bitcoin|crypto|coin", "coin"), (r"world|global|countr|war|china|europe|trade|tariff|economy", "earth"),
           (r"stock|market|index|shares|price|rally", "chart"), (r"money|cash|profit|debt|loan|billion|trillion", "moneybag")]
PHOTOS = [("federal reserve", "Federal Reserve building Washington"), ("wall street", "Wall Street New York"), ("data center", "data center servers"),
          ("oil", "oil refinery"), ("housing", "suburban houses aerial"), ("factory", "factory assembly line"), ("bank", "bank building"),
          ("stock exchange", "New York Stock Exchange"), ("gold", "gold bars"), ("shipping", "container ship port")]
BREAKING = re.compile(r"announc|breaking|just|reported|reveal|according|said|unveil|launch|statement|declared", re.I)
DEFINE = re.compile(r"\bmeans?\b|called|known as|is when|refers? to|defined|in simple terms|basically|think of", re.I)
CYCLE = re.compile(r"cycle|loop|spiral|feedback|vicious|again and again|repeat", re.I)
NEGATION = re.compile(r"\b(not|no|never|without|nobody|nothing|isn't|won't|can't|doesn't|don't|fail|failed)\b", re.I)
YEAR = re.compile(r"\b(19[89]\d|20[0-3]\d)\b")


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def back(x):
    x = max(0.0, min(1.0, x))
    return 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2


def icon_for(t):
    for rx, k in ICONS:
        if re.search(rx, t, re.I):
            return k
    return "bars"


def key_phrase(t):
    low = t.lower()
    for p in PHRASES:
        if p.lower() in low:
            return p[0].upper() + p[1:]
    allw = re.findall(r"[A-Za-z0-9&$%']+", t)
    ws = [w for w in allw if w.lower() not in S.STOP and len(w) > 3 and not re.search(r"(ly|ed|ing|es)$", w.lower())]
    top = sorted(set(ws), key=len, reverse=True)[:2]
    out = " ".join(w for w in allw if w in top)
    return out[:30] if out else "The Big Picture"


def find_stat(t):
    for m in STAT.finditer(t):
        s = m.group(0).strip()
        if re.fullmatch(r"(19|20)\d\d", re.sub(r"\D", "", s)) and not re.search(r"%|percent|illion", s):
            continue
        return s.replace(" percent", "%").replace("percent", "%")
    return None


def mascot_for(t):
    for rx, k in MASCOTS:
        if re.search(rx, t, re.I):
            return k
    return None


def mood_of(t):
    neg, pos = bool(NEG.search(t)), bool(POS.search(t))
    if neg and not pos:
        return "shock" if re.search(r"crash|plunge|collapse|panic|burst|wipe", t, re.I) else "sad"
    if pos and not neg:
        return "happy"
    return "neutral"


def pick_gesture(text, k, side):
    pt = "point_L" if side in ("L", "U") else "point_R"
    if "?" in text:
        return "palms_up"
    m = mood_of(text)
    if m in ("shock", "sad"):
        return ["worry", "think", "shrug"][k % 3]
    if m == "happy":
        return ["cheer", "fist_R", "open_both"][k % 3]
    if re.search(r"\bbut\b|however|twist|yet\b|actually|instead", text, re.I):
        return "chop_R" if k % 2 else "chop_L"
    if re.search(r"\d", text):
        return pt
    return ["open_both", "open_L", "open_R", "hips", "open_both", "think"][k % 6]


def plan(units, script, ev, mode, dur):
    tgt = 8.0 if mode == "long" else 4.2
    scenes, cur = [], []

    def flush():
        if cur:
            scenes.append({"units": list(cur), "start": cur[0]["start"], "sec": cur[0]["sec"], "text": " ".join(u["text"] for u in cur)})
            cur.clear()
    for u in units:
        if cur and (u["sec"] != cur[-1]["sec"] or u["end"] - cur[0]["start"] >= tgt):
            flush()
        cur.append(u)
    flush()
    for i, s in enumerate(scenes):
        s["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else dur
    scenes[0]["start"] = 0.0
    hl_i, charts, cd, prev_sec, ph_i = 0, 0, 0, -1, 0
    last_used, last_persona = {}, None
    n = len(scenes)
    for i, s in enumerate(scenes):
        t, low = s["text"], s["text"].lower()
        sid, kind = None, None
        cool = lambda k, gap: i - last_used.get(k, -99) >= gap
        pers = PU.find_persona(t)
        if not pers and last_persona and re.search(r"\b(he|she|his|her|him)\b", low):
            pers = last_persona
        last_persona = pers or (last_persona if i - last_used.get("pers", -99) < 2 else None)
        if pers:
            last_used["pers"] = i
        photo_q = next((q for kw, q in PHOTOS if kw in low), None)
        if i == 0:
            kind = "title"
        elif i == n - 1:
            kind = "outro"
        else:
            if cd <= 0 and charts < 9:
                for rx, k, *_ in S.SERIES:
                    if re.search(rx, low):
                        if k in ev["series"] or S.get_series(k, ev):
                            sid = k
                        break
            if sid:
                kind, cd, charts = "chart", 2, charts + 1
            elif YEAR.search(t) and cool("year", 4):
                kind = "year"
            elif CYCLE.search(t) and cool("cycle", 6):
                kind = "cycle"
            elif BREAKING.search(t) and cool("newspaper", 5):
                kind = "newspaper"
            elif DEFINE.search(t) and cool("board", 4):
                kind = "board"
            elif find_stat(t) and cool("stat", 2):
                kind = "stat"
            elif ev["headlines"] and i % 5 == 3 and cool("headline", 4):
                kind = "headline"
            elif photo_q and cool("photo", 9):
                kind = "photo"
            elif (mascot_for(t) or NEGATION.search(t)) and cool("mascot", 2):
                kind = "mascot"
            else:
                kind = "keyword"
        cd -= 1
        last_used[kind] = i
        s.update(kind=kind, series=sid, idx=i, persona=pers or "host", photo_q=photo_q,
                 hl=ev["headlines"][hl_i % len(ev["headlines"])] if ev["headlines"] else None)
        if kind == "headline":
            hl_i += 1
        s["mood"] = mood_of(t)
        s["banner"] = script["sections"][s["sec"]]["title"] if (mode == "long" and s["sec"] != prev_sec and s["sec"] > 0) else None
        prev_sec = s["sec"]
        side = "L" if i % 2 == 0 else "R"          # side of the CONTENT relative to the character (L = content on the left)
        s["cside"] = side
        g = []
        for k, u in enumerate(s["units"]):
            name = pick_gesture(u["text"], i + k, side if mode == "long" else "U")
            if kind in ("board",):
                name = "point_L" if side == "L" else "point_R"
            if kind == "title":
                name = "open_both"
            if kind == "outro":
                name = "wave"
            g.append((u["start"], u["end"] + 0.4, name))
            if u["end"] - u["start"] > 3.6:             # long sentence: change gesture mid-way, like a person would
                mid = (u["start"] + u["end"]) / 2
                g[-1] = (u["start"], mid, name)
                g.append((mid, u["end"] + 0.4, ["open_L", "open_R", "hips", "open_both"][(i + k) % 4]))
        s["gest"] = g
    sfx = []
    for s in scenes:
        k = s["kind"]
        sfx.append((s["start"] + .05, {"stat": "ding", "chart": "whoosh", "headline": "whoosh", "title": "whoosh", "newspaper": "whoosh",
                                         "board": "pop", "mascot": "pop", "photo": "whoosh", "year": "swish", "cycle": "swish"}.get(k, "pop")))
        if s["mood"] == "shock":
            sfx.append((s["start"] + .1, "thud"))
    return scenes, sfx


def words_timeline(units):
    words = []
    for u in units:
        ws = u["text"].split()
        tot = sum(len(w) + 1 for w in ws)
        t = u["start"]
        for w in ws:
            d = (u["end"] - u["start"]) * (len(w) + 1) / tot
            words.append((w, t, t + d))
            t += d
    return words


def word_box(title, width, word):
    pad = 26
    f2 = art.font("sans", 34)
    lines = art.wrap_lines(title, f2, width - pad * 2)[:4]
    dm = ImageDraw.Draw(Image.new("L", (1, 1)))
    for li, l in enumerate(lines):
        j = l.find(word)
        if j >= 0:
            x = pad + dm.textlength(l[:j], font=f2)
            return int(x - 14), pad + 40 + li * 44 - 8, int(dm.textlength(word, font=f2) + 28), 58
    return None


class Renderer:
    def __init__(self, W, H, mode, voice, ev, title_text, words):
        self.W, self.H, self.mode, self.ev, self.title_text = W, H, mode, ev, title_text
        self.land = W > H
        hop = 1.0 / 12
        n = int(len(voice) / 24000 / hop) + 1
        self.env = np.array([np.sqrt(np.mean(voice[int(i * hop * 24000):int((i + 1) * hop * 24000)] ** 2) + 1e-12) if int(i * hop * 24000) < len(voice) else 0 for i in range(n)])
        act = self.env[self.env > 0.005]
        self.thr = max(0.02, float(np.percentile(act, 35))) if len(act) else 0.02
        self.p95 = max(self.thr * 2, float(np.percentile(act, 95))) if len(act) else 0.1
        self.hop = hop
        self.words, self.wstarts = words, [w[1] for w in words]
        self.pup = {}
        self.rng = random.Random(11)

    # ---------- layout ----------
    def layout(self, sc):
        W, H = self.W, self.H
        if self.land:
            cside = sc["cside"]
            right = cside == "L"                       # content on the left => character on the right
            sc["char_x"] = int(W * (.83 if right else .17))
            sc["reg"] = (50, 60, int(W * .66), H - 50) if right else (int(W * .34), 60, W - 50, H - 50)
            sc["ch_h"] = int(H * .64)
        else:
            sc["char_x"] = W // 2
            sc["reg"] = (50, 150, W - 50, int(H * .50))
            sc["ch_h"] = int(H * .36)

    def put(self, sc, img, ax, ay, t0, anim, dur=.5, **kw):
        x0, y0, x1, y1 = sc["reg"]
        rw, rh = x1 - x0, y1 - y0
        sc_ = min(1.0 if (self.land or kw.get("keep")) else 1.8, rw / img.width, rh / img.height)
        if abs(sc_ - 1) > .02:
            img = img.resize((max(2, int(img.width * sc_)), max(2, int(img.height * sc_))), Image.LANCZOS)
        x = int(x0 + ax * rw - img.width / 2)
        y = int(y0 + ay * rh - img.height / 2)
        x = max(0, min(self.W - img.width, x))
        e = dict(img=img, x=x, y=y, t0=t0, anim=anim, dur=dur, dir=1 if sc["cside"] == "R" else -1, scale=sc_)
        e.update({k: v for k, v in kw.items() if k != "keep"})
        sc["E"].append(e)
        return e

    def prep(self, sc):
        k = sc["kind"]
        self.layout(sc)
        sc["E"] = []
        rw = sc["reg"][2] - sc["reg"][0]
        rh = sc["reg"][3] - sc["reg"][1]
        txt, dur = sc["text"], sc["end"] - sc["start"]
        mood = sc["mood"]
        if k == "title":
            self.put(sc, art.text_layer(self.title_text, "serif", int(rw * .15), maxw=rw), .5, .45, .05, "slide", .6)
        elif k == "chart":
            s = S.get_series(sc["series"], self.ev)
            cw, chh = rw, min(rh, int(rw * .62))
            img, xy = art.chart_layer(s["pts"], (cw, chh), s["title"], s["fmt"])
            rd = min(3.4, dur * .6)
            e = self.put(sc, img, .5, .5, .2, "crop", rd, keep=True)
            e["tip"] = xy
            up = s["pts"][-1][1] >= s["pts"][max(0, int(len(s["pts"]) * .86))][1]
            ar = art2.trend_arrow(int(cw * .30), int(chh * .34), up)
            self.put(sc, ar, .24, .30, .2 + rd * .85, "crop", .6, keep=True)
            tx, ty = xy[-1]
            ring = art2.red_circle(110, 110, 6)
            x0, y0 = e["x"], e["y"]
            sc["E"].append(dict(img=ring, x=int(x0 + tx - 55), y=int(y0 + ty - 55), t0=.2 + rd, anim="wedge", dur=.5, dir=1, scale=1))
        elif k == "stat":
            v = find_stat(txt) or "!"
            self.put(sc, art.stat_layer(v, key_phrase(txt), min(rw, 560 if self.land else 700)), .5, .42, .1, "pop", .45)
            mk = mascot_for(txt) or "moneybag"
            self.put(sc, art2.mascot(mk, 150 if self.land else 260), .12, .86, .7, "pop", .4)
            if mood in ("shock", "sad", "happy"):
                self.put(sc, art2.trend_arrow(170, 120, mood == "happy"), .86, .86, 1.0, "crop", .5)
        elif k == "headline":
            h = sc["hl"]
            card = art.headline_card(h["title"], h["source"], h["ago"], min(rw, 620 if self.land else rw))
            e = self.put(sc, card, .5, .4, .05, "slide", .45)
            nums = re.findall(r"\$?\d[\d,\.]*[%BMKbmk]?", h["title"])
            word = nums[0] if nums else max(h["title"].split(), key=len)
            bb = word_box(h["title"], card.width, word)
            if bb:
                bx, by, bw, bh = bb
                f = e["scale"]
                self.put(sc, art2.red_circle(int(bw * f * 1.0) + 8, int(bh * f * 1.1), 5), 0, 0, 1.1, "wedge", .5, keep=True)
                last = sc["E"][-1]
                last["x"], last["y"] = int(e["x"] + bx * f), int(e["y"] + by * f)
            self.put(sc, art2.bubble({"shock": "Uh oh...", "sad": "Not great.", "happy": "Wow!"}.get(mood, "Hmm."), 40), .5, .86, 1.7, "pop", .35)
        elif k == "board":
            self.put(sc, art2.board(key_phrase(txt), int(rw * .95), int(rw * .95 * .58)), .5, .45, .05, "pop", .45)
        elif k == "newspaper":
            label = "BREAKING NEWS!!!" if re.search(r"breaking|just|announc|unveil", txt, re.I) else "NEWS"
            self.put(sc, art2.newspaper(label, int(min(rw, 560) * .95)), .5, .4, .05, "pop", .45)
            self.put(sc, art2.bubble(key_phrase(txt), 40, 360, "right"), .5, .87, .9, "pop", .35)
        elif k == "mascot":
            mk = mascot_for(txt) or "earth"
            self.put(sc, art2.mascot(mk, int(min(rw, rh) * .5)), .42, .5, .05, "pop", .45)
            self.put(sc, art2.bubble(key_phrase(txt), 40, 360), .62, .17, .85, "pop", .35)
            if NEGATION.search(txt):
                self.put(sc, art2.cross_out(int(min(rw, rh) * .62)), .42, .5, 1.5, "wedge", .5)
        elif k == "photo":
            ph = media.find_photo(sc["photo_q"])
            if ph is not None:
                self.put(sc, art2.photo_card(ph, min(rw, 640 if self.land else rw)), .5, .45, .05, "slide", .5)
                self.put(sc, art2.handwritten(key_phrase(txt), 54, rw, art.INK, "center"), .5, .9, .8, "crop", .6)
            else:
                sc["kind"] = "mascot"
                return self.prep(sc)
        elif k == "year":
            y = YEAR.search(txt).group(1)
            self.put(sc, art2.handwritten(y, int(rw * .28), rw, art.INK, "center"), .5, .42, .05, "crop", .9)
            ul = Image.new("RGBA", (int(rw * .6), 14), (0, 0, 0, 0))
            ImageDraw.Draw(ul).line([(4, 8), (ul.width - 4, 5)], fill=art.RED, width=9)
            self.put(sc, ul, .5, .62, .9, "crop", .5)
            self.put(sc, art2.handwritten(key_phrase(txt), 48, rw, art.INK, "center"), .5, .8, 1.3, "pop", .35)
        elif k == "cycle":
            self.put(sc, art2.cycle_arrows(int(min(rw, rh) * .7)), .5, .45, .05, "wedge", 1.2)
            self.put(sc, art2.handwritten(key_phrase(txt), 52, rw, art.INK, "center"), .5, .9, .9, "pop", .35)
        elif k == "outro":
            img = Image.new("RGBA", (int(rw * .9), int(rw * .3)), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=img.height // 2, fill=art.RED)
            d.text((img.width / 2, img.height / 2), "SUBSCRIBE", font=art.font("sans", int(img.height * .38)), fill="white", anchor="mm")
            self.put(sc, img, .5, .45, .1, "pop", .45)
        else:  # keyword
            ph = key_phrase(txt)
            ic = art.icon_layer(icon_for(txt), int(min(rw, rh) * .36))
            tx = art.text_layer(ph, "hand", int(rw * .12), maxw=rw, hl=art.YELLOW, align="center")
            img = Image.new("RGBA", (max(tx.width, ic.width), ic.height + tx.height + 20), (0, 0, 0, 0))
            img.paste(ic, ((img.width - ic.width) // 2, 0), ic)
            img.paste(tx, ((img.width - tx.width) // 2, ic.height + 20), tx)
            self.put(sc, img, .5, .45, .05, "pop", .45)
            if mood in ("shock", "sad", "happy"):
                self.put(sc, art2.trend_arrow(150, 105, mood == "happy"), .88, .15, 1.0, "crop", .5)
        # persona decorations
        sc["deco"] = []
        pers = sc["persona"]
        ch_h = sc["ch_h"]
        if pers != "host":
            pw = int(ch_h * .62)
            pod = art2.podium(pw)
            sc["deco"].append(("front", pod, sc["char_x"] - pw // 2, self.H - 24 - pod.height + 6))
            if pers == "trump":
                fl = art2.flag(int(ch_h * .34))
                sc["deco"].append(("back", fl, sc["char_x"] - int(ch_h * .52), self.H - 30 - ch_h + 20))
        sc["bn"] = art.banner_layer(sc["banner"], 34 if self.land else 40) if sc["banner"] else None
        nm = PU.PERSONAS[pers]["name"]
        sc["nm"] = art.banner_layer(nm, 30 if self.land else 38) if nm else None

    # ---------- per-frame ----------
    def draw_elem(self, cv, e, lt):
        t = lt - e["t0"]
        if t < 0:
            return
        im, x, y, a = e["img"], e["x"], e["y"], e["anim"]
        u = t / max(.05, e["dur"])
        if a == "pop":
            kk = .5 + .5 * back(u)
            if u < 1.4 and abs(kk - 1) > .01:
                w, h = max(2, int(im.width * kk)), max(2, int(im.height * kk))
                im2 = im.resize((w, h), Image.BILINEAR)
                cv.paste(im2, (x + (im.width - w) // 2, y + (im.height - h) // 2), im2)
                return
            cv.paste(im, (x, y), im)
        elif a == "slide":
            kk = ease(u)
            x += int((1 - kk) * self.W * .22 * e["dir"])
            if kk < 1:
                im = im.copy()
                im.putalpha(im.getchannel("A").point(lambda v: int(v * kk)))
            cv.paste(im, (x, y), im)
        elif a == "crop":
            f = ease(u)
            w = max(2, int(im.width * f))
            part = im.crop((0, 0, w, im.height))
            cv.paste(part, (x, y), part)
            if e.get("tip") and f < 1:
                px, py = e["tip"][min(len(e["tip"]) - 1, int(f * (len(e["tip"]) - 1)))]
                ImageDraw.Draw(cv).ellipse([x + px - 9, y + py - 9, x + px + 9, y + py + 9], fill=art.RED)
        elif a == "wedge":
            im2 = art2.reveal_wedge(im, ease(u))
            cv.paste(im2, (x, y), im2)

    def state(self, pers):
        if pers not in self.pup:
            self.pup[pers] = PU.Spring()
        return self.pup[pers]

    def frame(self, sc, t):
        W, H = self.W, self.H
        cv = Image.new("RGB", (W, H), (255, 255, 255))
        lt = t - sc["start"]
        for kind, im, x, y in sc["deco"]:
            if kind == "back":
                cv.paste(im, (x, y), im)
        for e in sc["E"]:
            self.draw_elem(cv, e, lt)
        # --- character with real body language ---
        mi = min(len(self.env) - 1, int(t / self.hop))
        rms = float(self.env[mi])
        e_n = min(1.0, rms / self.p95)
        mouth = 2 if rms > self.thr * 2.6 else 1 if rms > self.thr else 0
        gname = "rest"
        for a, b, nme in sc["gest"]:
            if a - 0.15 <= t < b:
                gname = nme
                break
        tg = dict(PU.G[gname])
        if gname not in ("rest", "wave"):
            for kk in ("aL", "aR"):
                if tg[kk] > 30:
                    tg[kk] += 9 * e_n * (1 + .5 * math.sin(t * 7))      # arms pulse with speech emphasis
        if gname == "wave":
            tg["bR"] += 28 * math.sin(t * 9)
        tg["lean"] += 1.6 * math.sin(2 * math.pi * t / 3.7) + 1.2 * e_n
        tg["tilt"] += 2.2 * math.sin(2 * math.pi * t / 2.9 + 1)
        look = -1 if sc["cside"] == "L" else 1
        tg["lx"], tg["ly"] = (look * .8 if self.land else 0), (-.3 if not self.land else .1)
        pose = dict(self.state(sc["persona"]).step(tg, 1.0 / C.FPS))
        blink = 1 if (t % 3.6) < .13 else 0
        prop = "pointer" if gname.startswith("point") else ""
        mood = sc["mood"]
        ch = PU.draw(sc["persona"], pose, mouth, mood, blink, prop, sc["ch_h"])
        bob = int(3 * math.sin(2 * math.pi * t * 1.1))
        cv.paste(ch, (sc["char_x"] - ch.width // 2, H - 24 - ch.height + bob), ch)
        for kind, im, x, y in sc["deco"]:
            if kind == "front":
                cv.paste(im, (x, y), im)
        d = ImageDraw.Draw(cv)
        if sc["kind"] in ("keyword", "stat") and self.land:
            d.rectangle([0, H - 14, int(W * min(1, lt / max(.1, sc["end"] - sc["start"]))), H - 8], fill=art.YELLOW)
        if sc["bn"] is not None and lt < 3.4:
            kk = min(ease(lt / .4), ease((3.4 - lt) / .4))
            bw = sc["bn"].width
            cv.paste(sc["bn"], (int(-bw + (bw + 40) * kk), 24 if self.land else 60), sc["bn"])
        elif sc["nm"] is not None and lt < 3.6:
            kk = min(ease(lt / .4), ease((3.6 - lt) / .4))
            bw = sc["nm"].width
            cv.paste(sc["nm"], (int(-bw + (bw + 40) * kk), H - 100 if self.land else H - 150), sc["nm"])
        if self.mode == "short":
            i = bisect.bisect_right(self.wstarts, t) - 1
            if i >= 0:
                g = i // 3 * 3
                grp = self.words[g:g + 3]
                f = art.font("sans", 78)
                tw = [d.textlength(w[0].upper(), font=f) for w in grp]
                total = sum(tw) + 24 * (len(tw) - 1)
                cx0 = (W - total) / 2
                for j, w in enumerate(grp):
                    d.text((cx0, int(H * .53)), w[0].upper(), font=f, fill=art.YELLOW if g + j == i else (255, 255, 255),
                           stroke_width=8, stroke_fill=(0, 0, 0))
                    cx0 += tw[j] + 24
        # --- camera: slow push-in, small shake on bad news ---
        dur = max(.1, sc["end"] - sc["start"])
        z = 1.0 + (0.03 if sc["kind"] != "title" else 0.0) * min(1.0, lt / dur)
        dx = dy = 0
        if sc["mood"] == "shock" and lt < .55:
            dx, dy = self.rng.randint(-6, 6), self.rng.randint(-4, 4)
        if z > 1.001 or dx or dy:
            cw, chh = W / z, H / z
            l, tp = (W - cw) / 2 + dx, (H - chh) / 2 + dy
            cv = cv.transform((W, H), Image.EXTENT, (l, tp, l + cw, tp + chh), Image.BILINEAR)
        return cv


def render(scenes, words, voice, ev, audio_path, out_path, W, H, mode, dur, title_text):
    R = Renderer(W, H, mode, voice, ev, title_text, words)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(C.FPS), "-i", "-", "-i", audio_path, "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_path],
                          stdin=subprocess.PIPE)
    total, si = int(dur * C.FPS), 0
    for f in range(total):
        t = f / C.FPS
        while si + 1 < len(scenes) and t >= scenes[si]["end"]:
            for kk in ("E", "deco", "bn", "nm"):
                scenes[si].pop(kk, None)
            si += 1
        sc = scenes[si]
        if "E" not in sc:
            R.prep(sc)
        ff.stdin.write(R.frame(sc, t).tobytes())
        if f % (C.FPS * 60) == 0:
            print(f"render {f / total * 100:.0f}%", flush=True)
    ff.stdin.close()
    ff.wait()

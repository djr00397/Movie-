import re, math, bisect, subprocess
import numpy as np
from PIL import Image, ImageDraw
import config as C, art, sources as S

ICONS = [(r"crash|fall|plunge|drop|collapse|tumbl|slump|sell-?off|lose|loss|decline|down", "arrow_down"),
         (r"surge|rally|rise|record|soar|jump|gain|boom|climb|up\b", "arrow_up"),
         (r"bank|fed\b|federal|reserve|central|govern", "bank"),
         (r"risk|warn|danger|fear|bubble|crisis|panic|trouble", "warning"),
         (r"profit|money|cash|dollar|wealth|billion|million|trillion|rich", "moneybag"),
         (r"bond|yield|treasur|debt|loan|credit|margin|borrow", "bill"),
         (r"compan|firm|business|ceo|job|work|layoff|worker|employ", "briefcase"),
         (r"bitcoin|crypto|coin", "coin")]
NEG = re.compile(r"crash|fall|plunge|drop|collapse|tumbl|slump|sell-?off|loss|decline|risk|fear|bubble|crisis|panic|trouble|hurt|pain|debt|danger|warn|recession|worse", re.I)
POS = re.compile(r"surge|rally|record|soar|jump|gain|boom|climb|profit|growth|rich|win|strong|rise|better", re.I)
PHRASES = ["interest rates", "margin debt", "inflation", "recession", "stock market", "bond yields", "unemployment", "federal reserve",
           "tariffs", "the bubble", "the crash", "national debt", "housing market", "bitcoin", "oil prices", "earnings", "layoffs",
           "hedge funds", "credit", "the dollar", "gold", "supply chain", "GDP", "trade war", "private credit", "volatility"]
STAT = re.compile(r"\$\s?\d[\d,\.]*\s?(?:trillion|billion|million|thousand)?|\d[\d,\.]*\s?(?:%|percent|trillion|billion|million)")


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


def mood_pose(t):
    neg, pos = bool(NEG.search(t)), bool(POS.search(t))
    if neg and not pos:
        return ("shock" if re.search(r"crash|plunge|collapse|panic|record", t, re.I) else "sad"), ("shock" if "crash" in t.lower() else "sad"), ""
    if pos and not neg:
        return "happy", "money", "bag"
    if "?" in t:
        return "neutral", "idle", ""
    if re.search(r"\d", t):
        return "neutral", "point", "pointer"
    return "neutral", "idle", ""


def plan(units, script, ev, mode, dur):
    tgt = 7.5 if mode == "long" else 4.0
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
    hl_i, last, charts, cd, prev_sec = 0, [], 0, 0, -1
    for i, s in enumerate(scenes):
        t, low = s["text"], s["text"].lower()
        kind, sid = None, None
        if i == 0:
            kind = "title"
        elif i == len(scenes) - 1:
            kind = "outro"
        else:
            if cd <= 0 and charts < 9:
                for rx, k, *_ in S.SERIES:
                    if re.search(rx, low):
                        if k in ev["series"] or S.get_series(k, ev):
                            sid = k
                        break
            if sid:
                kind, cd = "chart", 2
                charts += 1
            elif find_stat(t) and (not last or last[-1] != "stat"):
                kind = "stat"
            elif i % 4 == 3 and ev["headlines"] and (not last or last[-1] != "headline"):
                kind = "headline"
            else:
                kind = "keyword"
        cd -= 1
        s.update(kind=kind, series=sid, idx=i, hl=ev["headlines"][hl_i % len(ev["headlines"])] if ev["headlines"] else None)
        if kind == "headline":
            hl_i += 1
        s["mood"], s["pose"], s["prop"] = mood_pose(t)
        s["hat"] = "tophat" if re.search(r"billionaire|wall street|rich|hedge fund", low) else ""
        if kind == "title":
            s["mood"], s["pose"], s["prop"] = "shock", "point", "pointer"
        if kind == "outro":
            s["mood"], s["pose"], s["prop"] = "happy", "wave", ""
        s["banner"] = script["sections"][s["sec"]]["title"] if (mode == "long" and s["sec"] != prev_sec and s["sec"] > 0) else None
        prev_sec = s["sec"]
        last.append(kind)
    ev_sfx = [(s["start"], "pop" if s["kind"] == "stat" else "whoosh") for s in scenes if s["kind"] in ("chart", "headline", "stat", "title")]
    return scenes, ev_sfx


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


class Renderer:
    def __init__(self, W, H, mode, voice, ev, title_text, words):
        self.W, self.H, self.mode, self.ev, self.title_text = W, H, mode, ev, title_text
        self.land = W > H
        hop = 1.0 / 12
        n = int(len(voice) / 24000 / hop) + 1
        self.env = np.array([np.sqrt(np.mean(voice[int(i * hop * 24000):int((i + 1) * hop * 24000)] ** 2) + 1e-12) if int(i * hop * 24000) < len(voice) else 0 for i in range(n)])
        self.thr = max(0.02, float(np.percentile(self.env[self.env > 0.005], 35))) if (self.env > 0.005).any() else 0.02
        self.hop = hop
        self.words, self.wstarts = words, [w[1] for w in words]

    def region(self, idx):
        W, H = self.W, self.H
        if self.land:
            right = idx % 2 == 0
            self.side = right
            return (50, 50, int(W * .66), H - 50) if right else (int(W * .34), 50, W - 50, H - 50)
        return (50, 150, W - 50, int(H * .53))

    def prep(self, sc):
        W, H = self.W, self.H
        x0, y0, x1, y1 = self.region(sc["idx"])
        rw, rh = x1 - x0, y1 - y0
        k, L = sc["kind"], {"dir": 1 if (not self.land or self.side) else -1}
        sc["reg"] = (x0, y0, x1, y1)
        if k == "title":
            img = art.text_layer(self.title_text, "serif", int(rw * .15), maxw=rw)
            L.update(img=img, reveal="slide")
        elif k == "chart":
            s = S.get_series(sc["series"], self.ev)
            img, xy = art.chart_layer(s["pts"], (rw, min(rh, int(rw * .62))), s["title"], s["fmt"])
            L.update(img=img, reveal="crop", xy=xy, rd=min(3.2, (sc["end"] - sc["start"]) * .7))
        elif k == "headline":
            h = sc["hl"]
            L.update(img=art.headline_card(h["title"], h["source"], h["ago"], min(rw, 620 if self.land else rw)), reveal="slide")
        elif k == "stat":
            v = find_stat(sc["text"])
            L.update(img=art.stat_layer(v, key_phrase(sc["text"]), min(rw, 560 if self.land else 700)), reveal="pop")
        elif k == "outro":
            img = Image.new("RGBA", (int(rw * .9), int(rw * .3)), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=img.height // 2, fill=art.RED)
            d.text((img.width / 2, img.height / 2), "SUBSCRIBE", font=art.font("sans", int(img.height * .38)), fill="white", anchor="mm")
            L.update(img=img, reveal="pop")
        else:
            ph = key_phrase(sc["text"])
            ic = art.icon_layer(icon_for(sc["text"]), int(min(rw, rh) * .38))
            tx = art.text_layer(ph, "hand", int(rw * .12), maxw=rw, hl=art.YELLOW, align="center")
            img = Image.new("RGBA", (max(tx.width, ic.width), ic.height + tx.height + 20), (0, 0, 0, 0))
            img.paste(ic, ((img.width - ic.width) // 2, 0), ic)
            img.paste(tx, ((img.width - tx.width) // 2, ic.height + 20), tx)
            L.update(img=img, reveal="pop")
        im = L["img"]
        sc_ = min(1.0 if (self.land or k == "chart") else 1.8, rw / im.width, rh / im.height)
        if abs(sc_ - 1) > .02:
            L["img"] = im.resize((int(im.width * sc_), int(im.height * sc_)), Image.LANCZOS)
            L["xy"] = [(x * sc_, y * sc_) for x, y in L.get("xy", [])]
        L["pos"] = (x0 + (rw - L["img"].width) // 2, y0 + (rh - L["img"].height) // 2)
        sc["L"] = L
        sc["bn"] = art.banner_layer(sc["banner"], 34 if self.land else 40) if sc["banner"] else None

    def frame(self, sc, t):
        W, H = self.W, self.H
        cv = Image.new("RGB", (W, H), (255, 255, 255))
        lt = t - sc["start"]
        L = sc["L"]
        im, (x, y) = L["img"], L["pos"]
        r = L["reveal"]
        if r == "slide":
            kk = ease(lt / .5)
            x += int((1 - kk) * W * .25 * L["dir"])
            if kk < 1:
                im = im.copy()
                im.putalpha(im.getchannel("A").point(lambda v: int(v * kk)))
            cv.paste(im, (x, y), im)
        elif r == "pop":
            kk = 0.55 + 0.45 * back(lt / .45)
            if abs(kk - 1) > .01 and lt < .6:
                w, h = max(2, int(im.width * kk)), max(2, int(im.height * kk))
                im2 = im.resize((w, h), Image.BILINEAR)
                cv.paste(im2, (x + (im.width - w) // 2, y + (im.height - h) // 2), im2)
            else:
                cv.paste(im, (x, y), im)
        else:
            f = ease(lt / L["rd"])
            w = max(2, int(im.width * f))
            part = im.crop((0, 0, w, im.height))
            cv.paste(part, (x, y), part)
            if L.get("xy") and f < 1:
                px, py = L["xy"][min(len(L["xy"]) - 1, int(f * (len(L["xy"]) - 1)))]
                ImageDraw.Draw(cv).ellipse([x + px - 9, y + py - 9, x + px + 9, y + py + 9], fill=art.RED)
        # character
        bob = int(6 * math.sin(2 * math.pi * lt * .9))
        mi = min(len(self.env) - 1, int(t / self.hop))
        mouth = 1 if self.env[mi] > self.thr else 0
        blink = 1 if (lt % 3.4) < .12 else 0
        ch_h = int(H * (.6 if self.land else .33))
        ch = art.character(sc["pose"], sc["mood"], mouth, sc["prop"], sc["hat"], blink, ch_h)
        cx = (int(W * .83) if self.side else int(W * .17)) if self.land else W // 2
        cv.paste(ch, (cx - ch.width // 2, H - 30 - ch.height + bob), ch)
        d = ImageDraw.Draw(cv)
        if sc["kind"] in ("keyword", "stat") and self.land:
            d.rectangle([0, H - 14, int(W * min(1, lt / max(.1, sc["end"] - sc["start"]))), H - 8], fill=art.YELLOW)
        if sc["bn"] is not None and lt < 3.4:
            kk = min(ease(lt / .4), ease((3.4 - lt) / .4))
            bw = sc["bn"].width
            bx = int(-bw + (bw + 40) * kk)
            cv.paste(sc["bn"], (bx, 24 if self.land else 60), sc["bn"])
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
                    d.text((cx0, int(H * .60)), w[0].upper(), font=f, fill=art.YELLOW if g + j == i else (255, 255, 255),
                           stroke_width=8, stroke_fill=(0, 0, 0))
                    cx0 += tw[j] + 24
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
            scenes[si].pop("L", None)
            si += 1
        sc = scenes[si]
        if "L" not in sc:
            R.region(sc["idx"])
            R.prep(sc)
        R.region(sc["idx"])
        ff.stdin.write(R.frame(sc, t).tobytes())
        if f % (C.FPS * 60) == 0:
            print(f"render {f / total * 100:.0f}%", flush=True)
    ff.stdin.close()
    ff.wait()

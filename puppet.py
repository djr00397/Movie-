"""Original rigged cartoon characters (not stick figures): body, sleeves, hands, face, hair, glasses, outfits.
Arms use 2-bone angles so gestures (open palms, pointing, shrug, cheer, think, panic...) animate like real body language."""
import math, re
from functools import lru_cache
from PIL import Image, ImageDraw
import art

INK = (32, 28, 36)
W0, H0, SS, OX = 560, 700, 2, 80

PERSONAS = {
    "host":   dict(name="", skin=(226, 176, 132), hair="curly", hc=(48, 34, 30), glasses="round", top=(238, 178, 52), kind="sweater",
                   shirt=(255, 255, 255), tie=None, bottom=(72, 84, 120), shoe=(245, 245, 245), sleeves="long"),
    "trump":  dict(name="Donald Trump", skin=(244, 176, 120), hair="swoop", hc=(248, 200, 96), glasses=None, top=(34, 40, 74), kind="suit",
                   shirt=(252, 252, 252), tie=(204, 32, 44), tie_long=True, bottom=(34, 40, 74), shoe=(20, 20, 24), sleeves="long"),
    "powell": dict(name="Jerome Powell", skin=(236, 190, 156), hair="side", hc=(176, 176, 182), glasses="rect", top=(44, 52, 84), kind="suit",
                   shirt=(252, 252, 252), tie=(60, 100, 170), bottom=(44, 52, 84), shoe=(20, 20, 24), sleeves="long"),
    "musk":   dict(name="Elon Musk", skin=(236, 190, 156), hair="short", hc=(60, 44, 36), glasses=None, top=(28, 28, 32), kind="tshirt",
                   shirt=(28, 28, 32), tie=None, bottom=(40, 44, 60), shoe=(30, 30, 34), sleeves="short"),
    "huang":  dict(name="Jensen Huang", skin=(232, 184, 140), hair="swept", hc=(30, 28, 32), glasses=None, top=(26, 26, 30), kind="jacket",
                   shirt=(250, 250, 250), tie=None, bottom=(30, 30, 38), shoe=(24, 24, 28), sleeves="long"),
    "zuckerberg": dict(name="Mark Zuckerberg", skin=(240, 196, 160), hair="curly", hc=(150, 108, 74), glasses=None, top=(150, 154, 160), kind="tshirt",
                   shirt=(150, 154, 160), tie=None, bottom=(60, 70, 96), shoe=(240, 240, 240), sleeves="short"),
    "buffett": dict(name="Warren Buffett", skin=(240, 196, 166), hair="side", hc=(238, 238, 242), glasses="round", top=(70, 70, 82), kind="suit",
                   shirt=(252, 252, 252), tie=(150, 40, 50), bottom=(70, 70, 82), shoe=(30, 24, 22), sleeves="long"),
    "dimon":  dict(name="Jamie Dimon", skin=(238, 192, 160), hair="side", hc=(214, 214, 220), glasses=None, top=(36, 46, 80), kind="suit",
                   shirt=(252, 252, 252), tie=(70, 110, 190), bottom=(36, 46, 80), shoe=(20, 20, 24), sleeves="long"),
    "altman": dict(name="Sam Altman", skin=(238, 192, 160), hair="short", hc=(104, 76, 56), glasses=None, top=(92, 100, 112), kind="sweater",
                   shirt=(255, 255, 255), tie=None, bottom=(50, 56, 76), shoe=(240, 240, 240), sleeves="long"),
    "bezos":  dict(name="Jeff Bezos", skin=(238, 190, 154), hair="bald", hc=(120, 100, 90), glasses=None, top=(40, 60, 96), kind="suit",
                   shirt=(252, 252, 252), tie=None, bottom=(40, 60, 96), shoe=(24, 24, 28), sleeves="long"),
    "lagarde": dict(name="Christine Lagarde", skin=(240, 196, 166), hair="bob", hc=(214, 214, 222), glasses=None, top=(60, 90, 140), kind="suit",
                   shirt=(252, 252, 252), tie=None, bottom=(60, 90, 140), shoe=(30, 24, 22), sleeves="long"),
    "yellen": dict(name="Janet Yellen", skin=(240, 196, 166), hair="bob", hc=(236, 214, 150), glasses=None, top=(170, 60, 80), kind="suit",
                   shirt=(252, 252, 252), tie=None, bottom=(170, 60, 80), shoe=(30, 24, 22), sleeves="long"),
}
NAME_RX = [(r"\btrump\b", "trump"), (r"\bpowell\b", "powell"), (r"\bmusk\b", "musk"), (r"\bhuang\b|\bjensen\b", "huang"),
           (r"\bzuckerberg\b", "zuckerberg"), (r"\bbuffett\b", "buffett"), (r"\bdimon\b", "dimon"), (r"\baltman\b", "altman"),
           (r"\bbezos\b", "bezos"), (r"\blagarde\b", "lagarde"), (r"\byellen\b", "yellen")]


def find_persona(text):
    for rx, k in NAME_RX:
        if re.search(rx, text, re.I):
            return k
    return None


# ---- gestures: (upper-arm angle, elbow bend) per arm, viewer's left arm 'L' / right arm 'R' ----
G = {
    "rest":      dict(aL=14, bL=12, aR=14, bR=12, tilt=0, lean=0, brow=0),
    "open_both": dict(aL=52, bL=78, aR=52, bR=78, tilt=2, lean=0, brow=.4),
    "open_L":    dict(aL=58, bL=70, aR=16, bR=14, tilt=-3, lean=-1, brow=.2),
    "open_R":    dict(aL=16, bL=14, aR=58, bR=70, tilt=3, lean=1, brow=.2),
    "palms_up":  dict(aL=44, bL=96, aR=44, bR=96, tilt=6, lean=0, brow=.9),
    "shrug":     dict(aL=38, bL=92, aR=38, bR=92, tilt=8, lean=0, brow=.6),
    "point_L":   dict(aL=96, bL=8, aR=14, bR=12, tilt=-3, lean=-3, brow=.2),
    "point_R":   dict(aL=14, bL=12, aR=96, bR=8, tilt=3, lean=3, brow=.2),
    "chop_R":    dict(aL=18, bL=16, aR=70, bR=48, tilt=2, lean=2, brow=-.3),
    "chop_L":    dict(aL=70, bL=48, aR=18, bR=16, tilt=-2, lean=-2, brow=-.3),
    "cheer":     dict(aL=150, bL=20, aR=150, bR=20, tilt=0, lean=0, brow=.8),
    "fist_R":    dict(aL=14, bL=12, aR=140, bR=70, tilt=3, lean=2, brow=.4),
    "think":     dict(aL=30, bL=-100, aR=40, bR=135, tilt=-8, lean=0, brow=.1),
    "worry":     dict(aL=118, bL=100, aR=118, bR=100, tilt=0, lean=-2, brow=.7),
    "hips":      dict(aL=38, bL=-112, aR=38, bR=-112, tilt=-2, lean=0, brow=0),
    "cross":     dict(aL=26, bL=-150, aR=26, bR=-150, tilt=3, lean=0, brow=-.2),
    "wave":      dict(aL=14, bL=12, aR=150, bR=40, tilt=4, lean=2, brow=.5),
}
PARAMS = ("aL", "bL", "aR", "bR", "tilt", "lean", "brow", "lx", "ly")


class Spring:
    """Critically-damped-ish spring so limbs ease into poses and overshoot slightly, like a real person."""
    def __init__(self):
        self.x = {k: 0.0 for k in PARAMS}
        self.v = {k: 0.0 for k in PARAMS}
        self.x.update(G["rest"])

    def step(self, target, dt):
        n = 4
        h = dt / n
        for _ in range(n):
            for k in PARAMS:
                a = 150.0 * (target.get(k, 0.0) - self.x[k]) - 17.0 * self.v[k]
                self.v[k] += a * h
                self.x[k] += self.v[k] * h
        return self.x


def _rot(p, c, deg):
    a = math.radians(deg)
    dx, dy = p[0] - c[0], p[1] - c[1]
    return (c[0] + dx * math.cos(a) - dy * math.sin(a), c[1] + dx * math.sin(a) + dy * math.cos(a))


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw(persona, pose, mouth=0, mood="neutral", blink=0, prop="", height=520):
    """pose: dict with aL,bL,aR,bR,tilt,lean,brow,lx,ly. mouth 0/1/2. Returns RGBA image of given height."""
    P = PERSONAS[persona]
    S = SS
    im = Image.new("RGBA", (W0 * S, H0 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hip = (200, 410)
    lean, tilt = pose.get("lean", 0), pose.get("tilt", 0)
    T = lambda p: _rot(p, hip, lean)
    s = lambda p: ((p[0] + OX) * S, p[1] * S)
    skin, dark = P["skin"], _lerp(P["skin"], (0, 0, 0), .18)

    def circle(c, r, fill, outline=INK, w=3):
        d.ellipse([s((c[0] - r, c[1] - r)), s((c[0] + r, c[1] + r))], fill=fill, outline=outline, width=int(w * S) if outline else 0)

    def limb(pts, w, col, ol=3.2):
        pts = [s(p) for p in pts]
        d.line(pts, fill=INK, width=int((w + 2 * ol) * S), joint="curve")
        for p in (pts[0], pts[-1]):
            r = (w / 2 + ol) * S
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=INK)
        d.line(pts, fill=col, width=int(w * S), joint="curve")
        for p in (pts[0], pts[-1]):
            r = (w / 2) * S
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)

    # legs + shoes
    for hx, fx in ((178, 168), (222, 232)):
        limb([(hx, 400), (fx, 600)], 36, P["bottom"])
        d.ellipse([s((fx - 30, 592)), s((fx + 30, 624))], fill=P["shoe"], outline=INK, width=int(3 * S))
    # torso
    tp = [T(p) for p in [(146, 238), (254, 238), (250, 404), (150, 404)]]
    d.polygon([s(p) for p in tp], fill=P["top"], outline=INK, width=int(3.5 * S))
    k = P["kind"]
    if k == "suit":
        v = [T(p) for p in [(180, 238), (220, 238), (200, 322)]]
        d.polygon([s(p) for p in v], fill=P["shirt"], outline=INK, width=int(2.5 * S))
        if P.get("tie"):
            L = 392 if P.get("tie_long") else 360
            t = [T(p) for p in [(194, 250), (206, 250), (212, L - 40), (200, L), (188, L - 40)]]
            d.polygon([s(p) for p in t], fill=P["tie"], outline=INK, width=int(2 * S))
        d.line([s(T((200, 322))), s(T((200, 404)))], fill=INK, width=int(2 * S))
    elif k in ("sweater", "tshirt", "jacket"):
        col = P["shirt"] if k == "jacket" else _lerp(P["top"], (0, 0, 0), .2)
        d.pieslice([s(T((172, 214))), s(T((228, 270)))], 0, 180, fill=col, outline=INK, width=int(2.5 * S))
        if k == "jacket":
            d.line([s(T((200, 262))), s(T((200, 404)))], fill=(90, 90, 98), width=int(3 * S))
    # arms (viewer-left arm uses mirrored angles)
    sleeve = P["top"] if P["sleeves"] == "long" else skin
    hands = {}
    for side, sx in (("L", 154), ("R", 246)):
        a, b = pose.get("a" + side, 14), pose.get("b" + side, 12)
        sg = -1 if side == "L" else 1
        sh = T((sx, 262))
        up = (sh[0] + sg * 84 * math.sin(math.radians(a)), sh[1] + 84 * math.cos(math.radians(a)))
        fa = a + b
        fo = (up[0] + sg * 78 * math.sin(math.radians(fa)), up[1] + 78 * math.cos(math.radians(fa)))
        limb([sh, up], 30, P["top"] if P["kind"] != "tshirt" else P["top"])
        limb([up, fo], 26 if P["sleeves"] == "long" else 22, sleeve if P["sleeves"] == "long" else skin)
        hands[side] = (fo, (fa))
    for side in ("L", "R"):
        fo, fa = hands[side]
        sg = -1 if side == "L" else 1
        hd = (fo[0] + sg * 12 * math.sin(math.radians(fa)), fo[1] + 12 * math.cos(math.radians(fa)))
        circle(hd, 17, skin)
        hands[side] = (hd, fa)
    # props in right hand
    if prop == "pointer":
        hd, fa = hands["R"]
        dx, dy = math.sin(math.radians(fa)), math.cos(math.radians(fa))
        d.line([s(hd), s((hd[0] + dx * 140, hd[1] + dy * 140))], fill=(120, 80, 40), width=int(7 * S))
        e = (hd[0] + dx * 140, hd[1] + dy * 140)
        circle(e, 6, (214, 39, 40))
    elif prop == "bag":
        hd, _ = hands["R"]
        art.draw_icon(d, "moneybag", (hd[0] + OX) * S, (hd[1] - 36) * S, 44 * S)
    elif prop == "doc":
        hd, _ = hands["L"]
        d.rectangle([s((hd[0] - 28, hd[1] - 50)), s((hd[0] + 28, hd[1] + 14))], fill=(252, 252, 246), outline=INK, width=int(3 * S))
        for i in range(4):
            d.line([s((hd[0] - 18, hd[1] - 38 + i * 12)), s((hd[0] + 18, hd[1] - 38 + i * 12))], fill=(214, 39, 40) if i == 0 else (150, 150, 150), width=int(2 * S))
    # neck + head (tilts about the neck base)
    nb = T((200, 232))
    HP = lambda dx, dy: _rot(T((200 + dx, 150 + dy)), nb, tilt)
    d.rectangle([s((nb[0] - 15, nb[1] - 24)), s((nb[0] + 15, nb[1] + 6))], fill=dark, outline=INK, width=int(3 * S))
    hc = HP(0, 0)
    # hair behind head
    hair = P["hair"]
    if hair in ("bob", "long"):
        d.rounded_rectangle([s((hc[0] - 76, hc[1] - 40)), s((hc[0] + 76, hc[1] + 78))], radius=40 * S, fill=P["hc"], outline=INK, width=int(3 * S))
    d.ellipse([s((hc[0] - 68, hc[1] - 74)), s((hc[0] + 68, hc[1] + 74))], fill=skin, outline=INK, width=int(4 * S))
    for ex in (-70, 70):
        e = HP(ex, 8)
        d.ellipse([s((e[0] - 11, e[1] - 16)), s((e[0] + 11, e[1] + 16))], fill=skin, outline=INK, width=int(3 * S))
    # front hair
    hcol = P["hc"]
    def poly(pts, col=hcol):
        d.polygon([s(HP(*p)) for p in pts], fill=col, outline=INK, width=int(3 * S))
    if hair == "curly":
        for i in range(8):
            a = math.radians(200 + i * 20)
            c = HP(math.cos(a) * 58, math.sin(a) * 62 - 6)
            circle(c, 25, hcol)
    elif hair == "swoop":
        poly([(-70, -10), (-62, -52), (-30, -80), (30, -84), (70, -56), (82, -40), (52, -48), (10, -42), (-30, -30), (-66, 6)])
        poly([(-30, -78), (20, -92), (74, -66), (90, -46), (40, -62), (-10, -60)], _lerp(hcol, (255, 255, 255), .15))
    elif hair == "side":
        poly([(-68, -4), (-62, -56), (-20, -80), (40, -78), (68, -46), (68, -6), (50, -44), (-4, -46), (-30, -30)])
    elif hair == "swept":
        poly([(-68, -2), (-60, -58), (-10, -84), (50, -76), (70, -40), (66, -6), (40, -52), (-10, -50), (-40, -24)])
    elif hair == "short":
        poly([(-68, -8), (-60, -56), (-20, -76), (30, -76), (64, -54), (68, -8), (50, -40), (0, -46), (-46, -38)])
    elif hair in ("bob", "long"):
        poly([(-70, 20), (-66, -50), (-20, -80), (40, -78), (70, -44), (70, 20), (48, -34), (0, -44), (-46, -30)])
    elif hair == "bald":
        for sx in (-1, 1):
            poly([(sx * 66, 0), (sx * 70, -24), (sx * 58, -28), (sx * 54, 0)])
    # face
    ey, eo = -4, 27
    mood_brow = {"angry": -1, "sad": .6, "shock": 1, "happy": .3}.get(mood, 0)
    br = max(-1, min(1, pose.get("brow", 0) + mood_brow))
    lx, ly = pose.get("lx", 0), pose.get("ly", 0)
    for sg in (-1, 1):
        c = HP(sg * eo, ey)
        if blink:
            d.line([s((c[0] - 12, c[1])), s((c[0] + 12, c[1]))], fill=INK, width=int(4 * S))
        else:
            rr = 15 if mood == "shock" else 13
            d.ellipse([s((c[0] - rr, c[1] - rr - 2)), s((c[0] + rr, c[1] + rr + 2))], fill=(255, 255, 255), outline=INK, width=int(3 * S))
            circle((c[0] + lx * 5, c[1] + ly * 4), 6, INK, None)
        by = -24 - br * 7
        slant = (-br if mood == "angry" else br) * 8 if mood in ("angry", "sad") else 0
        b0, b1 = HP(sg * (eo + 15), ey + by + sg * -slant * 0 + (slant if sg == -1 else -slant)), HP(sg * (eo - 15), ey + by - (slant if sg == -1 else -slant))
        d.line([s(b0), s(b1)], fill=INK if hair != "side" or P["hc"][0] < 200 else (110, 110, 118), width=int(4.5 * S))
    n0, n1 = HP(0, 8), HP(-3, 24)
    d.line([s(n0), s(n1), s(HP(7, 26))], fill=dark, width=int(3 * S))
    my = 44
    if mood == "shock" or mouth == 2:
        d.ellipse([s(HP(-14, my - 12)), s(HP(14, my + 16))], fill=(70, 24, 28), outline=INK, width=int(3 * S))
    elif mouth == 1:
        d.pieslice([s(HP(-22, my - 18)), s(HP(22, my + 20))], 0, 180, fill=(70, 24, 28), outline=INK, width=int(3 * S))
    elif mood == "sad":
        d.arc([s(HP(-18, my - 4)), s(HP(18, my + 20))], 200, 340, fill=INK, width=int(4 * S))
    else:
        d.arc([s(HP(-22, my - 14)), s(HP(22, my + 14))], 15, 165, fill=INK, width=int(4 * S))
    if P["glasses"]:
        for sg in (-1, 1):
            c = HP(sg * eo, ey)
            if P["glasses"] == "round":
                d.ellipse([s((c[0] - 21, c[1] - 21)), s((c[0] + 21, c[1] + 21))], outline=INK, width=int(4 * S))
            else:
                d.rounded_rectangle([s((c[0] - 22, c[1] - 17)), s((c[0] + 22, c[1] + 17))], radius=6 * S, outline=INK, width=int(4 * S))
        d.line([s(HP(-eo + 21, ey)), s(HP(eo - 21, ey))], fill=INK, width=int(4 * S))
    w = int(W0 * height / H0)
    return im.resize((w, height), Image.LANCZOS)

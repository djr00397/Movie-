from PIL import Image, ImageDraw
import art, sources as S


def make(text, ev, out):
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (255, 255, 255))
    words = text.split()
    k = max(1, (len(words) + 1) // 2)
    l1, l2 = " ".join(words[:k]), " ".join(words[k:])
    a = art.text_layer(l1, "serif", 92, maxw=int(W * .46))
    img.paste(a, (50, 70), a)
    y = 70 + a.height
    if l2:
        b = art.text_layer(l2, "serif", 108, maxw=int(W * .46))
        img.paste(b, (50, y), b)
        y += b.height
    d = ImageDraw.Draw(img)
    d.rectangle([56, y + 4, 56 + int(W * .30), y + 14], fill=art.RED)
    sid = ev.get("main")
    s = ev["series"].get(sid) if sid else None
    if s:
        cw, chh = int(W * .50), int(H * .56)
        ch, _ = art.chart_layer(s["pts"], (cw, chh), s["title"], s["fmt"])
        img.paste(ch, (int(W * .48), int(H * .06)), ch)
    else:
        ic = art.icon_layer("arrow_down", 380)
        img.paste(ic, (int(W * .56), int(H * .08)), ic)
    c1 = art.character("shock", "shock", 1, "", "", 0, 300)
    img.paste(c1, (-40, H - 300), c1)
    c2 = art.character("point", "angry", 0, "doc", "fedora", 0, 360)
    img.paste(c2, (int(W * .70), H - 360), c2)
    ic = art.icon_layer("moneybag", 150)
    img.paste(ic, (int(W * .50), H - 170), ic)
    img.save(out, "JPEG", quality=92)
    return out

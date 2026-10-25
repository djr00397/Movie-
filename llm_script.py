import re, os, gc, json
import config as C

_llm, _name = None, None


def llm(which):
    global _llm, _name
    if _name == which:
        return _llm
    _llm = None
    gc.collect()
    from llama_cpp import Llama
    from huggingface_hub import hf_hub_download
    repo, fn = C.MAIN_MODEL if which == "main" else C.FAST_MODEL
    path = hf_hub_download(repo, fn)
    _llm = Llama(model_path=path, n_ctx=6144, n_threads=os.cpu_count() or 2, verbose=False)
    _name = which
    return _llm


def chat(which, system, user, max_tokens=900, temp=0.7, as_json=False):
    kw = {"response_format": {"type": "json_object"}} if as_json else {}
    out = llm(which).create_chat_completion(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=max_tokens, temperature=temp, top_p=0.9, repeat_penalty=1.12, **kw)
    return out["choices"][0]["message"]["content"].strip()


# ---------- text helpers ----------
def wc(t):
    return len(t.split())


def split_sent(p):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", p.strip()) if s.strip()]


def clean(text):
    text = re.sub(r"[*#_`>]+", "", text)
    text = re.sub(r"(?mi)^\s*(chapter|section|part|narrator|voiceover|intro|outro)\b[^\n]*:?\s*$", "", text)
    text = re.sub(r"(?m)^\s*[-•]\s*", "", text)
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


def _nums(t):
    out = []
    for m in NUM.findall(t):
        try:
            out.append(m.replace(",", ""))
        except Exception:
            pass
    return out


def verify(text, ev_text):
    ev_nums = []
    for n in _nums(ev_text):
        try:
            ev_nums.append(float(n))
        except ValueError:
            pass
    ev_years = set(re.findall(r"\b(?:19|20)\d\d\b", ev_text))
    low_out = [o for o in C.OUTLETS]

    def good(s):
        ls = s.lower()
        if any(re.search(r"\b" + re.escape(o) + r"\b", ls) for o in low_out):
            return False
        for n in _nums(s):
            if re.fullmatch(r"(19|20)\d\d", n):
                if n not in ev_years:
                    return False
                continue
            try:
                v = float(n)
            except ValueError:
                continue
            pct = re.search(re.escape(n) + r"\s?(%|percent)", s)
            if v <= 10 and not pct:
                continue
            if not any(abs(v - e) <= 0.015 * abs(e) for e in ev_nums):
                return False
        return True

    keep = []
    for para in text.split("\n\n"):
        ok = [s for s in split_sent(para) if good(s)]
        if ok:
            keep.append(" ".join(ok))
    return "\n\n".join(keep)


def gen(topic, ev, instr, words, tail=""):
    best = ""
    for temp in (0.7, 0.5, 0.4):
        user = (f"TOPIC: {topic['title']}\n\nFACTS (the only allowed source for numbers, dates and names):\n{ev['text']}\n\n"
                + (f"THE PREVIOUS PART ENDED WITH: {tail}\n\n" if tail else "")
                + f"TASK: {instr} Aim for about {words} words. Rules: use a number, date or name ONLY if it appears in FACTS; "
                  f"otherwise explain in general terms. Do not repeat earlier parts. No headings, no lists.")
        raw = clean(chat("main", C.STYLE, user, int(words * 1.8) + 80, temp))
        txt = verify(raw, ev["text"])
        if wc(txt) > wc(best):
            best = txt
        if wc(best) >= words * 0.75:
            break
    return best


EXTRA = ["The Bigger Picture", "Lessons From History", "Myths And Misunderstandings", "What Ordinary People Should Watch"]
CTA_LONG = ("If you found this useful, subscribe and turn on notifications so you never miss the next story. "
            "This video is for education and information only, and it is not financial advice.")
CTA_SHORT = "Follow for a new money story every day."


def write_long(topic, ev):
    n = C.N_CHAPTERS
    raw = chat("main", C.STYLE,
               f"TOPIC: {topic['title']}\n\nFACTS:\n{ev['text'][:3500]}\n\nPlan an explainer video about this topic with exactly {n} chapters. "
               f"Return exactly {n} short chapter titles (2 to 6 words each), one per line, no numbering. The chapters must progress: "
               f"background, how it works, the numbers, who is affected, the risks, historical precedent, what comes next.", 160, 0.6)
    titles = []
    for l in raw.splitlines():
        l = re.sub(r"^[\d\.\-\)\s\*]+", "", l).strip(" \"*#:")
        if 3 <= len(l) <= 60:
            titles.append(l)
    fallback = ["The Backstory", "How It Actually Works", "The Numbers", "Who Is Affected", "The Hidden Risks",
                "Lessons From History", "What Happens Next"]
    titles = (titles + fallback)[:n] if len(titles) < n else titles[:n]
    secs = []
    hook = gen(topic, ev, "Write the opening hook of the video. Start with a shocking fact or a bold question taken from FACTS, "
               "do not greet the viewer, and end by teasing what they will learn.", C.HOOK_WORDS)
    secs.append({"title": "Intro", "text": hook})
    outline = "; ".join(titles)
    for i, t in enumerate(titles):
        tail = secs[-1]["text"][-260:]
        txt = gen(topic, ev, f"Write chapter {i + 1} of {n}, titled '{t}'. Full chapter list: {outline}. Cover only this chapter, "
                  f"in storytelling style, with at least one analogy.", C.CHAPTER_WORDS, tail)
        secs.append({"title": t, "text": txt})
        print("chapter", i + 1, wc(txt), "words")
    for t in EXTRA:
        if sum(wc(s["text"]) for s in secs) >= C.LONG_MIN_WORDS - C.CONCL_WORDS:
            break
        txt = gen(topic, ev, f"Write an extra chapter titled '{t}' that adds new insight.", C.CHAPTER_WORDS, secs[-1]["text"][-260:])
        secs.append({"title": t, "text": txt})
    concl = gen(topic, ev, "Write the conclusion: the key takeaways, what to watch next, and a balanced final thought. "
                "Do not give investment advice.", C.CONCL_WORDS, secs[-1]["text"][-260:])
    secs.append({"title": "Final Thoughts", "text": concl + "\n\n" + CTA_LONG})
    secs = [s for s in secs if wc(s["text"]) > 20]
    print("total words:", sum(wc(s["text"]) for s in secs))
    return {"sections": secs}


def write_short(topic, ev):
    txt = gen(topic, ev, "Write a 45-second YouTube Shorts narration. First sentence: a shocking hook. Then three or four punchy facts "
              "with plain-English explanations, then a surprising closing line. Very short sentences.", C.SHORT_WORDS)
    sents = split_sent(txt.replace("\n\n", " "))
    out, n = [], 0
    for s in sents:
        if n + wc(s) > C.SHORT_WORDS + 15:
            break
        out.append(s)
        n += wc(s)
    return {"sections": [{"title": "Short", "text": " ".join(out) + "\n\n" + CTA_SHORT}]}


# ---------- SEO ----------
def _strip(s, extra=()):
    s = re.sub(r"https?://\S+|www\.\S+|\S+\.(com|org|net|io|gov)\b\S*", "", s)
    for o in list(C.OUTLETS) + list(extra):
        s = re.sub(r"\b" + re.escape(o) + r"\b", "", s, flags=re.I)
    s = s.replace("<", "").replace(">", "")
    return re.sub(r"[ \t]{2,}", " ", s).strip()


def make_seo(topic, script, ev, mode, chapters):
    full = " ".join(s["text"] for s in script["sections"])
    jtxt = ""
    try:
        jtxt = chat("fast", "You are a senior YouTube SEO strategist for a finance explainer channel. Reply with JSON only.",
                    f"VIDEO TOPIC: {topic['title']}\nSCRIPT START: {full[:1100]}\n\nReturn JSON with keys: "
                    f"\"title\" (max 62 characters, curiosity-driven, includes the main keyword, truthful), "
                    f"\"hook\" (2 sentences, keyword-rich, describes the video), \"summary\" (3 sentences), "
                    f"\"tags\" (14 search phrases people type on YouTube), \"thumb_text\" (3 to 6 punchy words, like 'The Landing Will Hurt.'), "
                    f"\"hashtags\" (3 hashtags). Never mention any website, news outlet or link.", 600, 0.7, True)
        j = json.loads(jtxt)
    except Exception as ex:
        print("seo json fail", str(ex)[:80])
        j = {}
    base = re.sub(r"\s+", " ", topic["title"]).strip()
    title = _strip(str(j.get("title") or base)).strip(" \"'")[:66] or base[:66]
    hook = _strip(str(j.get("hook") or f"{base}. Here is what is really happening and why it matters for your money."))
    summ = _strip(str(j.get("summary") or "We break down the data, the history and the risks in plain English, step by step."))
    tags, tot = [], 0
    for t in (j.get("tags") or []) + topic["keys"] + ["finance", "stock market", "economy", "investing explained", "money"]:
        t = _strip(str(t)).strip("# ")
        if t and t.lower() not in [x.lower() for x in tags] and tot + len(t) < 440:
            tags.append(t)
            tot += len(t) + 1
    hs = [("#" + re.sub(r"\W", "", str(h))) for h in (j.get("hashtags") or []) if re.sub(r"\W", "", str(h))][:3] or ["#Finance", "#StockMarket", "#Economy"]
    thumb = _strip(str(j.get("thumb_text") or " ".join(title.split()[:5]))).strip()
    thumb = " ".join(thumb.split()[:6]) or "Markets Are Changing"
    if mode == "short":
        title = (title[:50].rstrip() + " #Shorts")
        desc = f"{hook}\n\n{summ}\n\nFollow for a new money story every day.\n\n{' '.join(hs)} #Shorts"
    else:
        ch = "\n".join(f"{ts} {name}" for ts, name in chapters) if chapters else ""
        desc = (f"{hook}\n\n{summ}\n\n" + (f"In this video:\n{ch}\n\n" if ch else "")
                + "Subscribe for clear, data-driven finance explainers every day.\nThis video is for education only and is not financial advice.\n\n"
                + f"{' '.join(hs)}\n\n" + ", ".join(tags[:12]))
    return {"title": title, "description": desc[:4900], "tags": tags, "thumb_text": thumb}

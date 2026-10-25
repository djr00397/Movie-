import re, os, json, glob, csv, io, time, datetime as dt, concurrent.futures as cf
from collections import Counter
import requests, feedparser
import config as C

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
GN = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q="
GN_QUERIES = ["stock+market", "wall+street", "federal+reserve", "inflation", "recession", "interest+rates",
              "treasury+yields", "bitcoin", "oil+prices", "earnings", "bank+crisis", "IPO", "tariffs+economy",
              "hedge+fund", "margin+debt", "housing+market", "AI+stocks", "jobs+report", "global+economy",
              "US+dollar", "gold+price", "national+debt", "private+credit", "bond+market", "nasdaq", "layoffs"]
FEEDS = [
    "https://www.cnbc.com/id/10000664/device/rss/rss.html", "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html", "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    "https://feeds.marketwatch.com/marketwatch/topstories/", "https://feeds.marketwatch.com/marketwatch/marketpulse/",
    "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/", "https://finance.yahoo.com/news/rssindex",
    "https://www.investing.com/rss/news.rss", "https://www.investing.com/rss/market_overview.rss",
    "https://seekingalpha.com/market_currents.xml", "https://www.federalreserve.gov/feeds/press_all.xml",
    "https://www.federalreserve.gov/feeds/speeches.xml", "https://www.bls.gov/feed/bls_latest.rss",
    "https://www.ecb.europa.eu/rss/press.html", "https://www.sec.gov/news/pressreleases.rss",
    "https://feeds.bbci.co.uk/news/business/rss.xml", "https://www.theguardian.com/uk/business/rss",
    "https://www.theguardian.com/business/economics/rss", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml", "https://rss.nytimes.com/services/xml/rss/nyt/YourMoney.xml",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
    "https://fortune.com/feed/", "https://feeds.businessinsider.com/custom/all",
    "https://cointelegraph.com/rss", "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://www.reddit.com/r/economics/top/.rss?t=day", "https://www.reddit.com/r/investing/top/.rss?t=day",
    "https://www.reddit.com/r/stocks/top/.rss?t=day", "https://www.reddit.com/r/finance/top/.rss?t=day",
    "https://www.aljazeera.com/xml/rss/all.xml", "https://www.theguardian.com/world/rss",
] + [GN + q + "+when:1d" for q in GN_QUERIES]

FIN = re.compile(r"stock|market|fed\b|federal reserve|inflation|interest rate|rate cut|rate hike|bond|yield|econom|bank|crypto|bitcoin|"
                 r"earning|gdp|recession|tariff|debt|ipo|dollar|oil|gold|trade|nasdaq|dow\b|s&p|treasury|invest|fund|hedge|margin|"
                 r"housing|mortgage|wall street|rally|selloff|sell-off|crash|bubble|layoff|jobs|unemployment|currency|billion|"
                 r"trillion|shares|profit|revenue|credit|loan|price|cpi|payroll|ecb|imf|opec|nvidia|apple|tesla|microsoft", re.I)
STOP = set("the a an of to in on for and or at by with from as is are was were be been it its this that these those after before over under "
           "into amid new says say said will could would may might than more most less how why what who when where about up down out off "
           "just not no yes you your we our their his her they them he she has have had but can cut hit hits".split())
GENERIC = {"stock", "stocks", "market", "markets", "price", "prices", "says", "wall", "street", "business", "news", "today", "week", "year"}
EVERGREEN = ["Stock market crash", "Yield curve inversion", "Margin call", "Quantitative easing", "Stagflation", "Hyperinflation",
             "Bretton Woods system", "Subprime mortgage crisis", "Dot-com bubble", "Black Monday (1987)", "Federal funds rate",
             "National debt of the United States", "Hedge fund", "Short squeeze", "Carry trade", "Credit default swap",
             "Sovereign wealth fund", "Gold standard", "Bank run", "Index fund", "Price-to-earnings ratio", "Recession",
             "Great Depression", "Asian financial crisis", "Global financial crisis of 2007-2008", "Federal Reserve", "Inflation",
             "Cryptocurrency bubble", "Private equity", "Exchange-traded fund"]

# keyword regex -> FRED series (id, title, transform, number format)
SERIES = [
    (r"nasdaq|tech stocks|ai stocks|nvidia|chip", "NASDAQCOM", "NASDAQ Composite Index", None, "{:,.0f}"),
    (r"\bdow\b|dow jones", "DJIA", "Dow Jones Industrial Average", None, "{:,.0f}"),
    (r"s&p|stock market|stocks|wall street|equit|rally|sell-?off|shares|bubble|crash|margin", "SP500", "S&P 500 Index", None, "{:,.0f}"),
    (r"inflation|cpi|consumer prices|cost of living", "CPIAUCSL", "US Inflation Rate (year over year, %)", "yoy", "{:.1f}%"),
    (r"interest rate|fed\b|federal reserve|rate cut|rate hike|powell|monetary", "FEDFUNDS", "Federal Funds Rate (%)", None, "{:.2f}%"),
    (r"treasur|yield|bond", "DGS10", "10-Year Treasury Yield (%)", None, "{:.2f}%"),
    (r"unemployment|jobs report|payroll|layoff|labor market", "UNRATE", "US Unemployment Rate (%)", None, "{:.1f}%"),
    (r"volatil|vix|fear gauge", "VIXCLS", "VIX Volatility Index", None, "{:.1f}"),
    (r"oil|crude|opec", "DCOILWTICO", "Crude Oil Price (USD per barrel)", None, "${:,.0f}"),
    (r"mortgage|housing|home price|real estate", "MORTGAGE30US", "30-Year Mortgage Rate (%)", None, "{:.2f}%"),
    (r"bitcoin|crypto", "CBBTCUSD", "Bitcoin Price (USD)", None, "${:,.0f}"),
    (r"dollar|currency|forex", "DTWEXBGS", "US Dollar Index", None, "{:.1f}"),
    (r"national debt|federal debt|deficit|government debt", "GFDEBTN", "US Federal Debt (millions USD)", None, "{:,.0f}"),
    (r"gdp|recession|economic growth|economy", "GDPC1", "US Real GDP Growth (year over year, %)", "yoy", "{:.1f}%"),
    (r"consumer sentiment|confidence|spending", "UMCSENT", "Consumer Sentiment Index", None, "{:.1f}"),
]
# backup source (monthly closes) for market series if FRED is unreachable from the runner
STOOQ = {"SP500": "^spx", "NASDAQCOM": "^ndq", "DJIA": "^dji", "VIXCLS": "^vix", "CBBTCUSD": "btc.v", "DCOILWTICO": "cl.f"}
_fred_cache = {}


def toks(s):
    return {w for w in re.findall(r"[a-z0-9&]+", s.lower()) if w not in STOP and len(w) > 2}


def jac(a, b):
    return len(a & b) / max(1, len(a | b))


def fetch_feed(url):
    out = []
    try:
        r = requests.get(url, headers=UA, timeout=20)
        d = feedparser.parse(r.content)
        for e in d.entries[:40]:
            title = re.sub(r"\s+", " ", e.get("title", "")).strip()
            src = (e.get("source") or {}).get("title") or d.feed.get("title", "")
            if "news.google.com" in url:
                title = re.sub(r"\s+-\s+[^-]+$", "", title)
            ts = time.mktime(e.published_parsed) if e.get("published_parsed") else time.time() - 86400
            summ = re.sub(r"<[^>]+>", " ", e.get("summary", ""))
            summ = re.sub(r"\s+", " ", summ).strip()[:400]
            if title:
                out.append({"title": title, "summary": summ, "link": e.get("link", ""), "source": src or url, "ts": ts})
    except Exception as ex:
        print("feed fail", url[:60], str(ex)[:60])
    return out


def gather():
    items = []
    with cf.ThreadPoolExecutor(12) as ex:
        for res in ex.map(fetch_feed, FEEDS):
            items += res
    items = [i for i in items if FIN.search(i["title"] + " " + i["summary"])]
    print("finance items:", len(items))
    return items


# ---------- history (one json file per published video, so parallel runs never conflict) ----------
def load_hist():
    out = []
    for f in glob.glob(os.path.join(C.HIST, "*.json")):
        try:
            out.append(json.load(open(f)))
        except Exception:
            pass
    return out


def save_hist(topic, mode, vid):
    rec = {"title": topic["title"], "keys": topic["keys"], "mode": mode, "video": vid, "ts": int(time.time())}
    json.dump(rec, open(os.path.join(C.HIST, f"{int(time.time())}-{mode}.json"), "w"))


def is_dup(title, keys, hist):
    t = toks(title)
    for h in hist:
        if jac(t, toks(h["title"])) >= 0.4 or len(set(keys) & set(h.get("keys", []))) >= 3:
            return True
    return False


def pick_topic(items, hist):
    items = sorted(items, key=lambda x: -x["ts"])
    cl = []
    for it in items:
        t = toks(it["title"])
        it["t"] = t
        for c in cl:
            if jac(t, c["t"]) >= 0.28 or len(t & c["t"]) >= 4:
                c["items"].append(it)
                break
        else:
            cl.append({"t": t, "items": [it]})
    now = time.time()
    for c in cl:
        its = c["items"]
        c["score"] = len({i["source"] for i in its}) * 3 + len(its) + (3 if now - its[0]["ts"] < 21600 else 1 if now - its[0]["ts"] < 86400 else 0)
    cl.sort(key=lambda c: -c["score"])
    for c in cl:
        cnt = Counter(w for i in c["items"] for w in toks(i["title"]) if w not in GENERIC)
        keys = [w for w, _ in cnt.most_common(5)]
        title = c["items"][0]["title"]
        if not is_dup(title, keys, hist):
            return {"title": title, "keys": keys, "items": c["items"], "evergreen": False}
    for name in EVERGREEN:
        keys = sorted(toks(name))[:5]
        if not is_dup(name, keys, hist):
            return {"title": name, "keys": keys, "items": [], "evergreen": True}
    return {"title": EVERGREEN[int(time.time()) % len(EVERGREEN)] + " explained", "keys": [], "items": [], "evergreen": True}


# ---------- evidence ----------
def article_text(url):
    if not url or "news.google.com" in url or "reddit.com" in url:
        return ""
    try:
        import trafilatura
        d = trafilatura.fetch_url(url)
        return (trafilatura.extract(d) or "")[:2600] if d else ""
    except Exception:
        return ""


def wiki(q, n=2):
    out = []
    try:
        r = requests.get("https://en.wikipedia.org/w/api.php", headers=UA, timeout=20,
                         params={"action": "query", "list": "search", "srsearch": q, "srlimit": n, "format": "json"}).json()
        for h in r["query"]["search"]:
            t = h["title"]
            s = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(t.replace(" ", "_")),
                             headers=UA, timeout=20).json()
            if s.get("extract"):
                out.append((t, s["extract"][:1500]))
    except Exception as ex:
        print("wiki fail", str(ex)[:60])
    return out


def _get(url, params, tries=3, timeout=90):
    for k in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout, params=params)
            if r.status_code == 200 and r.text.strip():
                return r.text
            print("http", r.status_code, url[:50])
        except Exception as ex:
            print("fetch retry", k + 1, url[:50], str(ex)[:80])
        time.sleep(3 * (k + 1))
    return None


def stooq_rows(sid):
    sym = STOOQ.get(sid)
    if not sym:
        return None
    txt = _get("https://stooq.com/q/d/l/", {"s": sym, "i": "m"}, 2, 40)
    if not txt:
        return None
    try:
        rows = [(r[0], float(r[4])) for r in list(csv.reader(io.StringIO(txt)))[1:] if len(r) >= 5 and r[4]]
        rows = [r for r in rows if r[0] >= "1995-01-01"]
        return rows if len(rows) > 20 else None
    except Exception:
        return None


def fred_series(sid, transform=None):
    if (sid, transform) in _fred_cache:
        return _fred_cache[(sid, transform)]
    rows = None
    txt = _get("https://fred.stlouisfed.org/graph/fredgraph.csv", {"id": sid, "cosd": "1995-01-01"})
    if txt:
        try:
            rows = [(a, float(b)) for a, b in list(csv.reader(io.StringIO(txt)))[1:] if b not in (".", "")]
            if transform == "yoy" and len(rows) > 12:
                d0 = [dt.date.fromisoformat(a) for a, _ in rows[:30]]
                gap = max(1, int(sorted((d0[i + 1] - d0[i]).days for i in range(len(d0) - 1))[len(d0) // 2]))
                lag = max(1, round(365 / gap))
                rows = [(rows[i][0], (rows[i][1] / rows[i - lag][1] - 1) * 100) for i in range(lag, len(rows))]
        except Exception as ex:
            print("fred parse fail", sid, str(ex)[:60])
            rows = None
    if (not rows or len(rows) <= 20) and transform is None:
        print("fred unavailable, trying backup source for", sid)
        rows = stooq_rows(sid)
    _fred_cache[(sid, transform)] = rows if rows and len(rows) > 20 else None
    return _fred_cache[(sid, transform)]


def series_for(sid):
    for rx, i, title, tr, fmt in SERIES:
        if i == sid:
            return rx, i, title, tr, fmt


def get_series(sid, ev):
    if sid in ev["series"]:
        return ev["series"][sid]
    rx, i, title, tr, fmt = series_for(sid)
    rows = fred_series(sid, tr)
    if not rows:
        return None
    step = max(1, len(rows) // 450)
    pts = rows[::step]
    if pts[-1] != rows[-1]:
        pts.append(rows[-1])
    last = rows[-1]
    prev = rows[max(0, len(rows) - 1 - (252 if len(rows) > 1500 else 12))]
    mx = max(rows, key=lambda r: r[1])
    chg = (last[1] / prev[1] - 1) * 100 if prev[1] else 0
    stats = (f"{title}: latest reading {fmt.format(last[1])} on {last[0]}; a year earlier it was about {fmt.format(prev[1])} "
             f"({chg:+.1f} percent change); the highest reading since 1995 was {fmt.format(mx[1])} on {mx[0]}.")
    ev["series"][sid] = {"title": title, "pts": pts, "fmt": fmt, "stats": stats}
    return ev["series"][sid]


def ago(ts):
    h = (time.time() - ts) / 3600
    return f"{int(h)} hours ago" if h < 24 else f"{int(h // 24)} day{'s' if h >= 48 else ''} ago"


def build_evidence(topic):
    items = topic["items"][:14]
    blob = topic["title"] + " " + " ".join(topic["keys"]) + " " + " ".join(i["title"] for i in items)
    ev = {"series": {}, "headlines": [], "main": None}
    parts = [f"TODAY: {dt.date.today().isoformat()} (the current year is {dt.date.today().year})."]
    # more headlines from Google News search for this exact topic
    extra = fetch_feed(GN + requests.utils.quote(" ".join(topic["keys"][:4]) or topic["title"]) + "+when:7d")[:10]
    seen = set()
    heads = []
    for i in items + extra:
        k = i["title"].lower()[:60]
        if k not in seen:
            seen.add(k)
            heads.append(i)
    ev["headlines"] = [{"title": h["title"], "source": h["source"], "ago": ago(h["ts"])} for h in heads[:8]]
    parts.append("NEWS HEADLINES AND SNIPPETS:\n" + "\n".join(f"- {h['title']}. {h['summary'][:220]}" for h in heads[:14]))
    urls = [h["link"] for h in items[:5]]
    with cf.ThreadPoolExecutor(5) as ex:
        arts = [a for a in ex.map(article_text, urls) if a][:3]
    if arts:
        parts.append("FULL ARTICLE EXCERPTS:\n" + "\n---\n".join(arts))
    q = topic["title"] if topic["evergreen"] else " ".join(topic["keys"][:3]) + " economy"
    w = wiki(q)
    if w:
        parts.append("BACKGROUND:\n" + "\n".join(f"{t}: {e}" for t, e in w))
    low = blob.lower()
    sids = [i for rx, i, *_ in SERIES if re.search(rx, low)][:3] or ["SP500"]
    for sid in sids:
        s = get_series(sid, ev)
        if s:
            ev["main"] = ev["main"] or sid
    if ev["series"]:
        parts.insert(1, "DATA:\n" + "\n".join(s["stats"] for s in ev["series"].values()))
    ev["text"] = "\n\n".join(parts)[:9500]
    print("evidence chars:", len(ev["text"]), "series:", list(ev["series"]))
    return ev

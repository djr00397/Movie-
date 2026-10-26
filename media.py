"""Free, legally reusable images from Wikimedia Commons (public domain / CC0 only, so no attribution is needed).
We do NOT scrape Google Images: that breaks Google's terms and brings copyright strikes."""
import io, os, re, hashlib
import requests
from PIL import Image
import config as C

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "FinanceExplainerBot/1.0 (educational video generator)"}
OK_LICENSE = re.compile(r"^(public domain|pd\b|cc0|cc-zero)", re.I)
_cache = {}


def find_photo(query):
    """Return a PIL image for the query, or None. Only public-domain / CC0 files are accepted."""
    key = query.lower().strip()
    if key in _cache:
        return _cache[key]
    img = None
    try:
        r = requests.get(API, headers=UA, timeout=20, params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": 6,
            "gsrlimit": 12, "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 900})
        pages = list((r.json().get("query") or {}).get("pages", {}).values())
        for p in pages:
            ii = (p.get("imageinfo") or [{}])[0]
            lic = ((ii.get("extmetadata") or {}).get("LicenseShortName") or {}).get("value", "")
            if not OK_LICENSE.search(lic) or ii.get("mime") not in ("image/jpeg", "image/png"):
                continue
            if ii.get("width", 0) < 500:
                continue
            b = requests.get(ii.get("thumburl") or ii["url"], headers=UA, timeout=30).content
            img = Image.open(io.BytesIO(b)).convert("RGB")
            break
    except Exception as ex:
        print("photo fail", query, str(ex)[:60])
    _cache[key] = img
    print("photo", query, "->", "ok" if img else "none")
    return img

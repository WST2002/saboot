"""Polite cached fetcher. Usage: python -I scripts/fetch.py URL [URL...]
Saves raw HTML to data/raw/<sha1>.html and appends to data/raw/index.jsonl.
Prints: status<TAB>path<TAB>url."""
import hashlib, json, os, sys, time, urllib.request, ssl, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
UA = "Mozilla/5.0 (research crawler; Saboot study; polite)"
DELAY = 3.0

def path_for(url):
    return os.path.join(RAW, hashlib.sha1(url.encode()).hexdigest()[:16] + ".html")

def fetch(url, force=False):
    p = path_for(url)
    if os.path.exists(p) and not force:
        return "cached", p
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "hi,en;q=0.8"})
    ctx = ssl.create_default_context()
    status = None
    try:
        try:
            r = urllib.request.urlopen(req, timeout=40, context=ctx)
        except ssl.SSLError:
            ctx = ssl._create_unverified_context()
            r = urllib.request.urlopen(req, timeout=40, context=ctx)
        status = r.status
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import gzip; data = gzip.decompress(data)
        with open(p, "wb") as f:
            f.write(data)
    except Exception as e:
        status = f"ERR {type(e).__name__}: {e}"[:200]
        p = ""
    with open(os.path.join(RAW, "index.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"url": url, "status": status, "path": os.path.relpath(p, ROOT) if p else "",
                            "fetched_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")}) + "\n")
    time.sleep(DELAY)
    return status, p

if __name__ == "__main__":
    for u in sys.argv[1:]:
        s, p = fetch(u)
        print(f"{s}\t{p}\t{u}")

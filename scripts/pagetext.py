"""Print visible text of a cached page (fetching it if needed), optionally only
lines matching a regex. Usage: python -I scripts/pagetext.py URL [REGEX]"""
import html as H, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import fetch
sys.stdout.reconfigure(encoding="utf-8")
st, p = fetch(sys.argv[1])
print("STATUS", st, p)
if p:
    raw = open(p, encoding="utf-8", errors="ignore").read()
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    t = H.unescape(re.sub(r"<[^>]+>", "\n", raw))
    lines = [re.sub(r"\s+", " ", x).strip() for x in t.split("\n")]
    lines = [x for x in lines if x]
    rx = re.compile(sys.argv[2]) if len(sys.argv) > 2 else None
    for x in lines:
        if rx is None or rx.search(x):
            print(x[:600])

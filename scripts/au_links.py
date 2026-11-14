"""Extract Amar Ujala article links (dated in URL, in window) from cached tag pages.
Usage: python -I scripts/au_links.py RAWFILE..."""
import re, sys
seen = set()
for fp in sys.argv[1:]:
    html = open(fp, encoding="utf-8", errors="ignore").read()
    for m in re.finditer(r'href="(?:https://www\.amarujala\.com)?(/[a-z0-9-]+(?:/[a-z0-9-]+)*?-(20\d\d-\d\d-\d\d))(?:[?"])', html):
        path, d = m.group(1), m.group(2)
        if any(path.startswith(x) for x in ("/photo-gallery", "/video", "/web-stories", "/shorts")):
            continue
        if not ("2026-08-01" <= d <= "2026-11-13"):
            continue
        if "src=top-subnav" in html[m.start():m.start()+len(path)+60]:
            continue
        u = "https://www.amarujala.com" + path
        if u not in seen:
            seen.add(u); print(d, u)

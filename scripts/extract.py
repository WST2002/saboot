"""Fetch article URLs (cached), extract published date, headline and candidate
claim sentences (scheme keyword + number). Appends to data/candidates.jsonl and
data/articles_log.jsonl (every article visited, for the denominator).
Usage: python -I scripts/extract.py data/article_urls.txt"""
import html as H
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import fetch, ROOT  # noqa: E402

SCHEMES = {
    "PM-KISAN": r"किसान सम्मान|पीएम[- ]?किसान|PM[- ]?Kisan|पीएम किसान",
    "PMAY": r"आवास योजना|पीएम आवास|PMAY|पीएमएवाई|प्रधानमंत्री आवास",
    "PMUY": r"उज्ज्वला|उज्जवला|PMUY|पीएमयूवाई",
    "JJM": r"जल जीवन|हर घर जल|नल से जल|नल[- ]जल|JJM",
    "PM-JAY": r"आयुष्मान|PM-?JAY|पीएम-?जय|वय वंदना",
    "MGNREGA": r"मनरेगा|नरेगा|जी[- ]?राम[- ]?जी|VB-?G|रामजी",
}
NUM = re.compile(r"[0-9०-९][0-9०-९,.]*\s*(?:लाख|करोड़|हजार|हज़ार|प्रतिशत|फीसदी|%)?")


def unjson(s):
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s


def text_of(raw):
    bodies = re.findall(r'"articleBody"\s*:\s*"((?:\\.|[^"\\])*)"', raw)
    if bodies:
        t = re.sub(r"<[^>]+>", " ", unjson(max(bodies, key=len)))
    else:
        ps = re.findall(r"<p[^>]*>(.*?)</p>", raw, flags=re.S)
        t = "\n".join(re.sub(r"<[^>]+>", " ", p) for p in ps)
    return re.sub(r"[ \t\xa0]+", " ", H.unescape(t))


def meta(raw):
    d = (re.search(r'"datePublished"\s*:\s*"([^"]+)"', raw)
         or re.search(r'article:published_time"\s*content="([^"]+)"', raw)
         or re.search(r'content="([^"]+)"\s*property="article:published_time"', raw))
    h = re.search(r'"headline"\s*:\s*"((?:\\.|[^"\\])*)"', raw) or re.search(r"<title>(.*?)</title>", raw, re.S)
    return (d.group(1) if d else ""), H.unescape(unjson(h.group(1)) if h else "").strip()


def sentences(t):
    for s in re.split(r"(?<=[।?!|])\s+|(?<=[^\d\s.]\.)\s+|\n+", t):
        s = s.strip()
        if 20 < len(s) < 700:
            yield s


def main(listfile):
    urls = [u.strip() for u in open(listfile, encoding="utf-8") if u.strip() and not u.startswith("#")]
    logp = os.path.join(ROOT, "data", "articles_log.jsonl")
    done = set()
    if os.path.exists(logp):
        done = {json.loads(line)["url"] for line in open(logp, encoding="utf-8")}
    with open(logp, "a", encoding="utf-8") as log, \
            open(os.path.join(ROOT, "data", "candidates.jsonl"), "a", encoding="utf-8") as out:
        for u in urls:
            if u in done:
                continue
            done.add(u)
            st, p = fetch(u)
            rec = {"url": u, "fetch_status": st,
                   "raw_path": os.path.relpath(p, ROOT).replace("\\", "/") if p else ""}
            if p:
                raw = open(p, encoding="utf-8", errors="ignore").read()
                d, hl = meta(raw)
                rec.update(pub_date=d, headline=hl)
                n = 0
                for s in sentences(text_of(raw)):
                    if NUM.search(s):
                        sch = [k for k, rx in SCHEMES.items() if re.search(rx, s)]
                        out.write(json.dumps({"url": u, "pub_date": d, "schemes": sch, "sentence": s},
                                             ensure_ascii=False) + "\n")
                        n += 1
                rec["n_numeric_sentences"] = n
            log.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log.flush()
            print(st, rec.get("pub_date", "")[:10], rec.get("n_numeric_sentences"), u[:110])


if __name__ == "__main__":
    main(sys.argv[1])

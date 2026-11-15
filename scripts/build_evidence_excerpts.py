"""Build and freeze the official-evidence excerpts for the evidence-given verifier condition (paper Section 3.4, C2).

Run once, before any model call. Writes data/evidence_excerpts.jsonl, one row per claim, with the exact
evidence block the model will see and its sha256. scripts/run_evidence.py refuses to run if a block's hash
no longer matches, and this script refuses to overwrite an existing file unless --force is given.

Source pages: the official page texts saved in the browser check (data/raw/pib_browser/<page>.txt, first line
the HTML title, second line "@@URL <url>"). Site navigation is dropped (PIB explainer pages: everything up to the
"Explainer Details" line) and so is the site footer (from the "(Release ID: ...)" / "(Explainer ID: ...)" line,
"Follow us on:", or the PIB footer lines). Page text is normalised (CR removed, runs of spaces and tabs to one
space, trailing spaces cut, 3+ newlines to 2); excerpts are verbatim substrings of the normalised text.

Rule A, bound and bound-ambiguous claims (46): the pages are the ones named in the claim's verification quotes
(data/bindings_verified.jsonl -> verification_quotes, the quotes read on the page in the browser check), in that
order. Each page gets a budget of 1,200 characters if the claim has one page, otherwise max(400, 1,500 // pages).
On each page, every verification quote is located (whitespace-insensitive); if all quotes fit in the budget they
share one window centred on them, otherwise each quote gets its own window and the windows are joined with
"[...]". A window is the quote span widened equally on both sides to the budget and cut at word boundaries.

Rule B, unbindable claims (56), "near-miss": the candidate pages are the saved pages for the same scheme (a page's
scheme is the scheme of the claims whose verification quotes cite it). Every 1,200-character window that starts
at a line start is scored: distinct content words of the claim's English gloss and metric key found in the window
(words of 3+ letters, digits, stop words and scheme-name words removed) plus 3 if the claim is state-level and the
window names the state (English or Hindi). Windows that contain the claim's own number in any written form
(plain, Western or Indian grouping, crore, lakh, lakh crore, English or Hindi) are excluded. The best window wins;
ties go to the page dated closest to the article date, then the earlier window. A claim whose best score is
0 (no same-scheme window shares a word with the claim) gets no excerpt (kind "none") and is not sent to the model.

Each row also records whether the excerpt contains the gold official figure (bound claims) or the claim's number
(should be false for near-miss), and, for near-miss rows, any number in the excerpt within 25% of the claim's
number (related_figures), so near-misses that might really be a mismatch can be reviewed by hand.
Usage: python -I -X utf8 scripts/build_evidence_excerpts.py [--force]"""
import argparse
import hashlib
import json
import os
import re
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
PAGES = os.path.join(DATA, "raw", "pib_browser")
OUT = os.path.join(DATA, "evidence_excerpts.jsonl")
RULE_VERSION = "2026-11-15 v1"
SINGLE, MULTI_TOTAL, MULTI_MIN, NEAR = 1200, 1500, 400, 1200
MIN_NEAR_SCORE = 1
STOP = set("""the and for with from that this than more over under about after before been were was are has have had into
which their they them there these those also only such other each every last year years month months total number per
said says claim claimed claims according government official stated given said rupees crore lakh percent scheme yojana
pradhan mantri india indian under nearly around almost approximately already since till until then while when where
will would could should being some most many much very just like through during across within without""".split())
SCHEME_WORDS = {
    "PM-KISAN": {"kisan", "samman", "nidhi"}, "PM-JAY": {"ayushman", "bharat", "arogya", "jan", "pmjay", "jay"},
    "JJM": {"jal", "jeevan", "mission", "jjm"}, "PMAY": {"awas", "awaas", "pmay", "gramin", "urban"},
    "PMUY": {"ujjwala", "pmuy"}, "MGNREGA/VB-G RAM G": {"mgnrega", "mgnregs", "vb-g", "ram", "rozgar"},
}
STATE_HI = {"Bihar": "बिहार", "Chhattisgarh": "छत्तीसगढ़", "Uttar Pradesh": "उत्तर प्रदेश", "Jharkhand": "झारखंड",
            "Rajasthan": "राजस्थान", "West Bengal": "पश्चिम बंगाल", "Gujarat": "गुजरात", "Uttarakhand": "उत्तराखंड",
            "Tamil Nadu": "तमिलनाडु"}
UNITS = ((1e12, ("lakh crore", "लाख करोड़")), (1e7, ("crore", "करोड़", "cr")), (1e5, ("lakh", "लाख")))
NUM_UNIT = re.compile(r"(?<![\d.])(\d[\d,]*(?:\.\d+)?)\s*(lakh crore|लाख करोड़|crore|करोड़|cr\b|lakh|लाख)?", re.I)
FOOTER = re.compile(r"^(\((Release|Explainer) ID: \d+\)|TendersArchives|The website belongs to|Follow us on:|Cookies on this website)")
MONTHS = {m: i for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split(), 1)}


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalise(text):
    text = text.replace("\r", "")
    text = re.sub(r"[ \t ]+", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def read_page(page_id):
    with open(os.path.join(PAGES, page_id + ".txt"), encoding="utf-8") as f:
        raw = f.read()
    lines = raw.split("\n")
    url = lines[1].removeprefix("@@URL ").strip()
    content = lines[2:]
    start = next((i + 1 for i, line in enumerate(content[:80]) if "Explainer Details" in line), 0)
    end = next((i for i, line in enumerate(content) if FOOTER.match(line.strip())), len(content))
    body = normalise("\n".join(content[start:end]))
    m = re.search(r"^(Posted On:.*|प्रविष्टि तिथि:.*)$", body, re.M)
    return {"page": page_id, "url": url, "body": body, "posted": m.group(1).strip() if m else None,
            "page_sha256": sha(raw)}


def posted_date(page):
    m = page["posted"] and re.search(r"(\d{1,2}) ([A-Z]{3}) (\d{4})", page["posted"])
    return date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1))) if m else None


def grouped(i):
    s = str(i)
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    indian = ",".join(([head] if head else []) + groups + [tail]) if len(s) > 3 else s
    return {s, f"{i:,}", indian}


def numerals(x):
    if float(x).is_integer():
        return grouped(int(x))
    return {f"{x:.2f}".rstrip("0").rstrip("."), f"{x:g}"}


def written_forms(x):
    """Ways a page may write the number x."""
    forms = numerals(x)
    for unit, words in UNITS:
        if x >= unit:
            v = round(x / unit, 2)
            forms |= {f"{n} {w}" for n in numerals(v) for w in words} | {f"{n}{w}" for n in numerals(v) for w in words}
    return forms


def contains_figure(text, x):
    flat = re.sub(r"\s+", " ", text).lower()
    return any(re.search(r"(?<!\d)(?<!\d[.,])" + re.escape(f.lower()) + r"(?![\d])(?!\.\d)", flat) for f in written_forms(x))


def numbers_in(text):
    out = []
    for m in NUM_UNIT.finditer(text):
        try:
            v = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        unit = (m.group(2) or "").lower()
        mult = next((u for u, ws in UNITS if unit in ws), 1)
        out.append((m.group(0).strip(), v * mult))
    return out


def locate(body, quote):
    pat = r"\s+".join(re.escape(w) for w in quote.split())
    m = re.search(pat, body)
    if not m:
        raise SystemExit(f"quote not found on page: {quote[:80]}: re-check data/bindings_verified.jsonl against data/raw/pib_browser/")
    return m.start(), m.end()


def window(body, a, b, budget):
    """Span [a, b) widened equally to `budget` characters, cut at word boundaries."""
    extra = max(0, budget - (b - a))
    start = max(0, a - extra // 2)
    end = min(len(body), start + max(budget, b - a))
    start = max(0, min(start, end - max(budget, b - a)))
    if start > 0:
        ws = re.search(r"\s", body[start:a])
        start = start + ws.end() if ws else start
    if end < len(body):
        ws = [m.start() for m in re.finditer(r"\s", body[b:end])]
        end = b + ws[-1] if ws else end
    return start, end


def render(text, start, end, body_len):
    return ("…" if start > 0 else "") + text.strip() + ("…" if end < body_len else "")


def page_block(n, page, windows):
    head = [f"[Official page {n}] URL: {page['url']}"]
    head.append(f"Page date line: {page['posted']}" if page["posted"] else "Page date line: none (live dashboard page)")
    head.append(f"Page retrieved: {page['retrieved']}")
    return "\n".join(head) + "\n<<<\n" + "\n[...]\n".join(windows) + "\n>>>"


def bound_row(claim, bind, pages):
    quotes = {}
    for q in bind["verification_quotes"]:
        quotes.setdefault(q["page"], []).append(q["quote"])
    budget = SINGLE if len(quotes) == 1 else max(MULTI_MIN, MULTI_TOTAL // len(quotes))
    blocks, used = [], []
    for n, (pid, qs) in enumerate(quotes.items(), 1):
        page = pages[pid]
        body = page["body"]
        spans = sorted({locate(body, q) for q in qs})
        if spans[-1][1] - spans[0][0] <= budget:
            groups = [(spans[0][0], spans[-1][1])]
        else:
            groups = spans
        texts, offs = [], []
        for a, b in groups:
            s, e = window(body, a, b, budget if len(groups) == 1 else max(MULTI_MIN, budget // len(groups)))
            texts.append(render(body[s:e], s, e, len(body)))
            offs.append([s, e])
        blocks.append(page_block(n, page, texts))
        used.append({"page": pid, "url": page["url"], "page_sha256": page["page_sha256"], "offsets": offs,
                     "posted": page["posted"], "quotes": qs})
    return blocks, used, {"rule": "A: windows around the verification quotes", "budget_per_page": budget}


def content_words(claim):
    words = set(re.findall(r"[a-z][a-z\-]{2,}", (claim["english_gloss"] + " " + claim["metric"].replace("_", " ")).lower()))
    return sorted(words - STOP - SCHEME_WORDS[claim["scheme"]])


def near_row(claim, cands, pages):
    words = content_words(claim)
    geo = claim["geography"] if claim["geography"] != "India" else None
    geo_terms = [geo.lower(), STATE_HI[geo]] if geo else []
    pub = date.fromisoformat(claim["pub_date"])
    best = None
    for pid in cands:
        page = pages[pid]
        body = page["body"]
        pdate = posted_date(page) or date.fromisoformat(page["retrieved"])
        starts = [0] + [m.end() for m in re.finditer(r"\n", body)]
        for st in starts:
            s, e = window(body, st, min(len(body), st + 1), NEAR)
            s = st
            text = body[s:e]
            low = text.lower()
            if contains_figure(text, claim["number"]):
                continue
            hits = [w for w in words if re.search(r"\b" + re.escape(w) + r"\b", low)]
            geo_hit = any(t in low for t in geo_terms)
            score = len(hits) + (3 if geo_hit else 0)
            key = (-score, abs((pdate - pub).days), s)
            if best is None or key < best[0]:
                best = (key, pid, s, e, hits, geo_hit, score)
    if best is None or best[6] < MIN_NEAR_SCORE:
        return None, None, {"rule": "B: near-miss window", "content_words": words,
                            "best_score": best[6] if best else None, "skipped": "no window shares a content word with the claim"}
    _, pid, s, e, hits, geo_hit, score = best
    page = pages[pid]
    text = render(page["body"][s:e], s, e, len(page["body"]))
    related = [t for t, v in numbers_in(text) if v and abs(v - claim["number"]) / claim["number"] <= 0.25]
    used = [{"page": pid, "url": page["url"], "page_sha256": page["page_sha256"], "offsets": [[s, e]], "posted": page["posted"]}]
    sel = {"rule": "B: near-miss window", "content_words": words, "matched_words": hits, "geography_hit": geo_hit,
           "score": score, "candidate_pages": cands, "related_figures": related}
    return [page_block(1, page, [text])], used, sel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite an existing frozen file (only before any model call)")
    args = ap.parse_args()
    if os.path.exists(OUT) and not args.force:
        raise SystemExit("data/evidence_excerpts.jsonl is frozen: pass --force only if no model call has used it yet")
    if not os.path.isdir(PAGES):
        raise SystemExit("data/raw/pib_browser/ missing: the saved official page texts are needed (not in the public repo)")
    claims = {c["id"]: c for c in load("claims.jsonl")}
    binds = {b["id"]: b for b in load("bindings_verified.jsonl")}
    checked = {r["evidence_id"]: r["checked_on"] for r in load("pib_verification.jsonl")}
    pages = {}
    for fn in sorted(os.listdir(PAGES)):
        pid = fn.removesuffix(".txt")
        pages[pid] = read_page(pid)
        pages[pid]["retrieved"] = checked.get(pid, checked.get(pid[:3], "2026-11-14"))
    scheme_pages = {}
    for b in binds.values():
        for q in b.get("verification_quotes") or []:
            scheme_pages.setdefault(claims[b["id"]]["scheme"], [])
            if q["page"] not in scheme_pages[claims[b["id"]]["scheme"]]:
                scheme_pages[claims[b["id"]]["scheme"]].append(q["page"])
    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for cid in sorted(claims):
        c, b = claims[cid], binds[cid]
        if b["label"] == "unbindable":
            blocks, used, sel = near_row(c, sorted(scheme_pages.get(c["scheme"], [])), pages)
            kind = "near_miss" if blocks else "none"
        else:
            blocks, used, sel = bound_row(c, b, pages)
            kind = "bound"
        block = "\n\n".join(blocks) if blocks else None
        row = {"claim_id": cid, "gold_label": b["label"], "kind": kind, "scheme": c["scheme"],
               "rule_version": RULE_VERSION, "built_at": built, "selection": sel, "pages": used,
               "evidence_block": block, "evidence_sha256": sha(block) if block else None,
               "chars": len(block) if block else 0}
        if block:
            row["contains_claim_figure"] = contains_figure(block, c["number"])
            if b["official_figure"] is not None:
                row["contains_gold_figure"] = contains_figure(block, b["official_figure"])
        rows.append(row)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    kinds = {k: sum(r["kind"] == k for r in rows) for k in ("bound", "near_miss", "none")}
    lens = sorted(r["chars"] for r in rows if r["chars"])
    print(f"wrote data/evidence_excerpts.jsonl: {kinds}; evidence block chars min {lens[0]}, median {lens[len(lens) // 2]}, max {lens[-1]}")
    bad = [r["claim_id"] for r in rows if r["kind"] == "bound" and r.get("contains_gold_figure") is False]
    leak = [r["claim_id"] for r in rows if r["kind"] == "near_miss" and r["contains_claim_figure"]]
    rel = [r["claim_id"] for r in rows if r["kind"] == "near_miss" and r["selection"]["related_figures"]]
    print(f"bound excerpts without the gold figure in a recognised form (check by hand): {bad or 'none'}")
    print(f"near-miss excerpts containing the claim's number (must be none): {leak or 'none'}")
    print(f"near-miss excerpts with a number within 25% of the claim (review): {rel or 'none'}")


if __name__ == "__main__":
    main()

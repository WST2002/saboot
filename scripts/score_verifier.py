"""Score the closed-book LLM-verifier run (paper Section 3.4, condition C1).

Reads data/verifier_results.jsonl (written by run_verifier.py), data/claims.jsonl and
data/bindings_verified.jsonl, and writes report/verifier_tables.md and
report/figures/fig2_verifier_verdicts.svg (+ .png). Every verifier number in the report
comes from here.

Scored model: gemini-3.5-flash-lite (all 102 claims x Hindi and English). gemini-3.8-flash
returned HTTP 503 (overloaded) on almost every call and is excluded; its row count is reported.

Verdict mapping (strict labels): bound+match -> SUPPORTED, bound+mismatch -> CONTRADICTED,
bound-ambiguous -> CANNOT_VERIFY (no clean official figure exists), unbindable -> CANNOT_VERIFY.

Source URLs the model cites are checked once each and cached in data/url_checks.jsonl
(GET, one request every 3 s). A URL that does not answer a plain GET (timeout, TLS error)
is re-checked in a real browser when --cdp <path to a CDP helper> is given; the helper is
called as `node <helper> <url> <jsfile>` and prints the JSON value of the script. The last
record for a URL wins. A PIB URL counts as resolving only if its PRID holds a release
(the page has an og:title).
Usage: python -I -X utf8 scripts/score_verifier.py [--cdp path/to/cdp.mjs]"""
import argparse
import hashlib
import html
import json
import math
import os
import re
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report_tables import INK, INK_2, GRID, SURFACE, svg_to_png, wilson  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
REPORT = os.path.join(ROOT, "report")
URL_CACHE = os.path.join(DATA, "url_checks.jsonl")
MODEL = "gemini-3.5-flash-lite"
EXCLUDED = "gemini-3.8-flash"
LANGS = ("hi", "en")
LANG_NAME = {"hi": "Hindi", "en": "English"}
LABELS = ["bound+match", "bound+mismatch", "bound-ambiguous", "unbindable"]
VERDICTS = ["SUPPORTED", "CONTRADICTED", "CANNOT_VERIFY"]
EXPECTED = {"bound+match": "SUPPORTED", "bound+mismatch": "CONTRADICTED",
            "bound-ambiguous": "CANNOT_VERIFY", "unbindable": "CANNOT_VERIFY"}
VERDICT_COLORS = {"SUPPORTED": "#2a78d6", "CONTRADICTED": "#eb6834", "CANNOT_VERIFY": "#9a9893"}
OFFICIAL = re.compile(r"(\.gov\.in|\.nic\.in|(^|\.)sansad\.in)$")
SCHEME_WORDS = {
    "PM-KISAN": ["kisan", "किसान"], "PM-JAY": ["ayushman", "arogya", "आयुष्मान"],
    "JJM": ["jal jeevan", "जल जीवन"], "PMAY": ["awas", "आवास", "housing"],
    "PMUY": ["ujjwala", "उज्ज्वला"], "MGNREGA/VB-G RAM G": ["mgnrega", "rozgar", "मनरेगा", "रोजगार"],
}
CONF_BINS = [(0.0, 0.5), (0.5, 0.8), (0.8, 0.9), (0.9, 0.95), (0.95, 1.01)]
UA = {"User-Agent": "Mozilla/5.0 (research link check; one request every 3 s)"}
BROWSER_JS = ("(() => { const m = document.querySelector('meta[property=\"og:title\"]'); "
              "return {href: location.href, title: document.title, og_title: m ? m.content : null, "
              "text: document.body ? document.body.innerText : ''}; })()")
PAGES = os.path.join(DATA, "raw", "url_pages")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def rate(k, n):
    if n == 0:
        return "n/a (0)"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% ({k}/{n}, 95% CI {100 * lo:.1f}-{100 * hi:.1f}%)"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_pib(url):
    return urllib.parse.urlparse(url).hostname.endswith("pib.gov.in")


def og_title(page):
    m = re.search(r'property="og:title"\s+content="(.*?)"', page, re.S)
    return html.unescape(m.group(1)).strip() if m and m.group(1).strip() else None


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, html.unescape(r.geturl()), r.read().decode("utf-8", "replace")


def save_text(url, text):
    """Page text is kept locally (data/raw/ is not republished) so figures can be searched again."""
    os.makedirs(PAGES, exist_ok=True)
    name = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12] + ".txt"
    with open(os.path.join(PAGES, name), "w", encoding="utf-8") as f:
        f.write(text)
    return name


def check_plain(url):
    rec = {"url": url, "checked_at": now(), "method": "urllib GET"}
    try:
        status, final, page = get(url)
        rec.update(status=status, final_url=final, page_title=og_title(page))
        rec["resolves"] = 200 <= status < 400 and (not is_pib(url) or rec["page_title"] is not None)
        if rec["resolves"]:
            text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.S)))
            rec["text_file"] = save_text(url, text)
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, resolves=False, error=f"HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, ConnectionError) as e:
        rec.update(status=None, resolves=False, error=str(getattr(e, "reason", e))[:200])
    return rec


def check_browser(url, cdp):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(BROWSER_JS)
        js = f.name
    try:
        out = subprocess.run(["node", cdp, url, js], capture_output=True, text=True, encoding="utf-8", timeout=120)
        val = json.loads(out.stdout) if out.stdout.strip() else None
    finally:
        os.unlink(js)
    rec = {"url": url, "checked_at": now(), "method": "browser (Chrome via CDP)"}
    if not val or val["href"].startswith(("chrome-error", "about:")) or len(val["text"]) < 200:
        rec.update(resolves=False, error="browser could not load the page", final_url=val and val["href"])
    else:
        rec.update(resolves=True, final_url=val["href"], page_title=val["og_title"] or val["title"],
                   text_file=save_text(url, val["text"]))
    return rec


def url_checks(urls, cdp):
    """Plain GET for every URL; non-PIB pages (often filled by JavaScript) are re-read in a browser when --cdp is given."""
    cache = {}
    if os.path.exists(URL_CACHE):
        for r in load("url_checks.jsonl"):
            cache[r["url"]] = r
    new = []
    for u in urls:
        if u not in cache:
            cache[u] = check_plain(u)
            new.append(cache[u])
            time.sleep(3)
        if cdp and not is_pib(u) and cache[u]["method"] == "urllib GET":
            cache[u] = check_browser(u, cdp)
            new.append(cache[u])
            time.sleep(3)
    if new:
        with open(URL_CACHE, "a", encoding="utf-8") as f:
            for r in new:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    for r in cache.values():
        r["official"] = bool(OFFICIAL.search(urllib.parse.urlparse(r["url"]).hostname or ""))
        path = os.path.join(PAGES, r.get("text_file") or "-")
        r["text"] = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    return cache


def figure_forms(x):
    """Ways an official page may write the number x (Western and Indian digit grouping, crore/lakh)."""
    forms = set()
    if float(x).is_integer():
        i = int(x)
        s = str(i)
        forms |= {s, f"{i:,}"}
        head, tail = s[:-3], s[-3:]
        if head:
            groups = []
            while len(head) > 2:
                groups.insert(0, head[-2:])
                head = head[:-2]
            forms.add(",".join(([head] if head else []) + groups) + "," + tail)
    else:
        forms.add(f"{x:g}")
    for unit, words in ((1e7, ("crore", "करोड़", "cr")), (1e5, ("lakh", "लाख"))):
        if x >= unit:
            v = f"{x / unit:.2f}".rstrip("0").rstrip(".")
            forms |= {f"{v} {w}" for w in words} | {f"{v}{w}" for w in words}
    return forms


def figure_on_page(text, value):
    flat = re.sub(r"\s+", " ", text).lower()
    return any(f.lower() in flat for f in figure_forms(value))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fmt(x):
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.2f}"


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value on b and c discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def svg_fig(path, panels, title, cats=VERDICTS, colors=VERDICT_COLORS, legend="Model verdict:"):
    """Horizontal 100% stacked bars of verdicts. panels: [(panel title, [(row name, Counter)])]."""
    width, left, right, bar_h, gap = 720, 230, 60, 20, 8
    plot_w = width - left - right
    y, body = 56, []
    for panel_title, rows in panels:
        body.append(f'<text x="{left}" y="{y}" font-size="13" font-weight="600" fill="{INK}">{escape(panel_title)}</text>')
        y += 12
        top = y
        for name, cnt in rows:
            n = sum(cnt.values())
            x = left
            segs = [(v, cnt[v]) for v in cats if cnt[v]]
            for i, (v, k) in enumerate(segs):
                w = plot_w * k / n
                inner = w - (2 if i < len(segs) - 1 else 0)
                body.append(f'<rect x="{x:.1f}" y="{y}" width="{max(inner, 0.5):.1f}" height="{bar_h}" fill="{colors[v]}"/>')
                if w >= 14:
                    ink = "#ffffff" if v != "CANNOT_VERIFY" else INK
                    body.append(f'<text x="{x + w / 2:.1f}" y="{y + 14}" font-size="11" text-anchor="middle" fill="{ink}">{k}</text>')
                x += w
            body.append(f'<text x="{left - 8}" y="{y + 14}" font-size="12" text-anchor="end" fill="{INK}">{escape(name)}</text>')
            body.append(f'<text x="{left + plot_w + 6}" y="{y + 14}" font-size="11" fill="{INK_2}">n={n}</text>')
            y += bar_h + gap
        for t in (0, 25, 50, 75, 100):
            gx = left + plot_w * t / 100
            body.insert(0, f'<line x1="{gx:.1f}" y1="{top - 4}" x2="{gx:.1f}" y2="{y - gap + 4}" stroke="{GRID}" stroke-width="1"/>')
            body.append(f'<text x="{gx:.1f}" y="{y + 8}" font-size="10" text-anchor="middle" fill="{INK_2}">{t}%</text>')
        y += 36
    body.append(f'<text x="{left - 8}" y="{y}" font-size="12" text-anchor="end" fill="{INK}">{escape(legend)}</text>')
    lx = left
    for v in cats:
        body.append(f'<rect x="{lx}" y="{y - 10}" width="12" height="12" rx="2" fill="{colors[v]}"/>')
        body.append(f'<text x="{lx + 17}" y="{y}" font-size="12" fill="{INK}">{v}</text>')
        lx += 40 + 7.5 * len(v)
    height = y + 18
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           f'font-family="Helvetica, Arial, sans-serif">', f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
           f'<text x="16" y="28" font-size="15" font-weight="600" fill="{INK}">{escape(title)}</text>'] + body + ["</svg>"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))
    return width, height


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp", help="CDP helper script for re-checking URLs a plain GET could not load")
    args = ap.parse_args()

    claims = {c["id"]: c for c in load("claims.jsonl")}
    bind = {b["id"]: b for b in load("bindings_verified.jsonl")}
    allrows = load("verifier_results.jsonl")
    rows = [r for r in allrows if r["model"] == MODEL]
    excluded = [r for r in allrows if r["model"] == EXCLUDED]
    assert len(rows) == 2 * len(claims), f"{MODEL}: expected {2 * len(claims)} rows, found {len(rows)}"
    by = {(r["claim_id"], r["lang"]): r for r in rows}
    for r in rows:
        r["label"] = bind[r["claim_id"]]["label"]
        r["expected"] = EXPECTED[r["label"]]
        r["correct"] = r["verdict"] == r["expected"]
    ids = sorted(claims)
    unparsed = sum(1 for r in rows if not r["parsed"])
    stamps = sorted(r["called_at"] for r in rows)

    L = ["# Saboot: LLM-verifier tables", "",
         "Generated by `scripts/score_verifier.py` from `data/verifier_results.jsonl`, `data/bindings_verified.jsonl`, "
         "`data/claims.jsonl` and `data/url_checks.jsonl`. Do not edit by hand. Percentages carry Wilson 95% intervals.", "",
         "## 1. Run", "",
         f"- Scored model: {MODEL}; condition C1 (closed-book: claim, scheme name and article date only); temperature 0.",
         f"- Rows: {len(rows)} ({len(claims)} claims x Hindi and English); unparsed answers: {unparsed}; "
         f"calls made {stamps[0]} to {stamps[-1]}.",
         f"- Excluded: {EXCLUDED}, {len(excluded)} answered call(s) out of {2 * len(claims)} planned (HTTP 503 overloaded on the rest).",
         "- Verdict expected for each label: " + ", ".join(f"{k} -> {v}" for k, v in EXPECTED.items()) + ".", ""]

    # 2. verdict counts and confusion
    L += ["## 2. Verdicts by gold label", "", "| Language | Gold label | n | SUPPORTED | CONTRADICTED | CANNOT_VERIFY |",
          "|---|---|---:|---:|---:|---:|"]
    conf = {}
    for lang in LANGS:
        for lab in LABELS:
            cnt = Counter(r["verdict"] for r in rows if r["lang"] == lang and r["label"] == lab)
            conf[(lang, lab)] = cnt
            L.append(f"| {LANG_NAME[lang]} | {lab} | {sum(cnt.values())} | " + " | ".join(str(cnt[v]) for v in VERDICTS) + " |")
    L += [""]

    # 3. agreement
    L += ["## 3. Verdict agreement with the gold labels", ""]
    for lang in LANGS + ("both",):
        rs = [r for r in rows if lang == "both" or r["lang"] == lang]
        name = "Both languages (204 answers)" if lang == "both" else LANG_NAME[lang]
        L.append(f"- {name}: all claims {rate(sum(r['correct'] for r in rs), len(rs))}")
        for lab in LABELS:
            sub = [r for r in rs if r["label"] == lab]
            L.append(f"  - {lab} (expected {EXPECTED[lab]}): {rate(sum(r['correct'] for r in sub), len(sub))}")
        clean = [r for r in rs if r["label"] in ("bound+match", "bound+mismatch")]
        L.append(f"  - cleanly bound claims (match or mismatch), verdict right: {rate(sum(r['correct'] for r in clean), len(clean))}")
    always_cv = sum(1 for r in rows if r["expected"] == "CANNOT_VERIFY")
    L += [f"- Baseline that always answers CANNOT_VERIFY: {rate(always_cv, len(rows))}.", ""]

    # 4. abstention
    L += ["## 4. Abstention (CANNOT_VERIFY rate)", ""]
    abst = {}
    for lang in LANGS + ("both",):
        rs = [r for r in rows if lang == "both" or r["lang"] == lang]
        name = "Both languages" if lang == "both" else LANG_NAME[lang]
        groups = {"unbindable": [r for r in rs if r["label"] == "unbindable"],
                  "bindable (any binding)": [r for r in rs if r["label"] != "unbindable"],
                  "cleanly bound": [r for r in rs if r["label"] in ("bound+match", "bound+mismatch")],
                  "ambiguous": [r for r in rs if r["label"] == "bound-ambiguous"]}
        for g, sub in groups.items():
            k = sum(r["verdict"] == "CANNOT_VERIFY" for r in sub)
            abst[(lang, g)] = (k, len(sub))
            L.append(f"- {name}, {g}: {rate(k, len(sub))}")
    future = [r for r in rows if r["verdict"] == "CANNOT_VERIFY" and re.search(r"future", r["reason"] or "", re.I)]
    cv_all = sum(r["verdict"] == "CANNOT_VERIFY" for r in rows)
    L += [f"- CANNOT_VERIFY answers whose reason says the article date is in the future: {len(future)}/{cv_all} "
          f"(Hindi {sum(r['lang'] == 'hi' for r in future)}, English {sum(r['lang'] == 'en' for r in future)}).", ""]

    # 5. committed answers
    committed = [r for r in rows if r["verdict"] != "CANNOT_VERIFY"]
    L += ["## 5. Committed answers (SUPPORTED or CONTRADICTED)", "",
          f"- Committed answers: {len(committed)}/{len(rows)}; correct verdict: {rate(sum(r['correct'] for r in committed), len(committed))}.",
          "- Committed answers by gold label: " + ", ".join(f"{lab} {sum(r['label'] == lab for r in committed)}" for lab in LABELS) + ".", "",
          "| Claim | Lang | Gold label | Verdict | Claimed | Model figure | Gold official figure | Model as-of | Confidence | Source URL |",
          "|---|---|---|---|---|---|---|---|---:|---|"]
    for r in sorted(committed, key=lambda r: (r["claim_id"], r["lang"])):
        c, b = claims[r["claim_id"]], bind[r["claim_id"]]
        mf = num(r["official_figure"])
        L.append(f"| {r['claim_id']} | {r['lang']} | {r['label']} | {r['verdict']} | {fmt(c['number'])} | "
                 f"{fmt(mf) if mf is not None else '-'} | {fmt(b['official_figure']) if b['official_figure'] is not None else '-'} | "
                 f"{r['as_of_date'] or '-'} | {r['confidence']} | {r['source_url'] or '-'} |")
    stale = [r for r in committed if r["as_of_date"] and r["as_of_date"][:4] < "2026"]
    L += ["", f"- Committed answers whose as-of date is before 2026 (all claims are from Aug-Nov 2026): {len(stale)}/{len(committed)}.", ""]

    # 6. sources
    urls = sorted({r["source_url"] for r in rows if r["source_url"]})
    checks = url_checks(urls, args.cdp)
    with_src = [r for r in rows if r["source_url"]]
    for r in with_src:
        ck = checks[r["source_url"]]
        fig = num(r["official_figure"])
        words = SCHEME_WORDS[claims[r["claim_id"]]["scheme"]]
        if not ck["official"]:
            r["src_kind"] = "not an official domain"
        elif not ck["resolves"]:
            r["src_kind"] = "did not load"
        elif is_pib(r["source_url"]) and not any(w in (ck.get("page_title") or "").lower() for w in words):
            r["src_kind"] = "PIB release on an unrelated subject"
        elif fig is not None and ck["text"] and figure_on_page(ck["text"], fig):
            r["src_kind"] = "page shows the stated figure"
        else:
            r["src_kind"] = "page loads but does not show the stated figure"
    kinds = Counter(r["src_kind"] for r in with_src)
    halluc = [r for r in with_src if r["src_kind"] != "page shows the stated figure"]
    certain = [r for r in halluc if r["src_kind"] != "did not load"]
    L += ["## 6. Cited sources", "",
          f"- Answers with a non-null source URL: {len(with_src)}/{len(rows)} (committed answers among them: "
          f"{sum(r['verdict'] != 'CANNOT_VERIFY' for r in with_src)}); distinct URLs: {len(urls)}.",
          "- Outcome of each cited source: " + ", ".join(f"{k} {v}" for k, v in kinds.most_common()) + ".",
          f"- Hallucinated source (methodology 4: URL does not resolve, resolves but does not show the stated figure, "
          f"or is not an official domain): {rate(len(halluc), len(with_src))}.",
          f"- Same, counting only pages that loaded (pages that did not load from our network left out): "
          f"{rate(len(certain), len(with_src) - kinds['did not load'])}.",
          f"- Not resolving or not an official domain (narrow definition): {rate(kinds['did not load'] + kinds['not an official domain'], len(with_src))}.",
          f"- PIB release IDs cited: {sum(is_pib(r['source_url']) for r in with_src)}; of these on an unrelated subject: "
          f"{kinds['PIB release on an unrelated subject']}.", "",
          "| URL | Cited in | Check | Loads | Outcome | Page title (as fetched) | Model's source title |",
          "|---|---|---|---|---|---|---|"]
    for u in urls:
        ck = checks[u]
        cited = [r for r in with_src if r["source_url"] == u]
        cites = ", ".join(f"{r['claim_id']}-{r['lang']}" for r in cited)
        titles = "; ".join(sorted({(r["source_title"] or "").replace("|", "/") for r in cited}))
        page_t = (ck.get("page_title") or ck.get("error") or "-").replace("|", "/")
        outcome = "; ".join(sorted({r["src_kind"] for r in cited}))
        L.append(f"| {u} | {cites} | {ck['method']}, {ck['checked_at'][:10]} | {ck['resolves']} | {outcome} | {page_t} | {titles} |")
    L += [""]

    # 7. figures
    fig_rows = [r for r in rows if num(r["official_figure"]) is not None]
    on_bound = [r for r in fig_rows if bind[r["claim_id"]]["official_figure"] is not None]
    L += ["## 7. Figure accuracy", "",
          f"- Answers giving an official figure: {len(fig_rows)}/{len(rows)}; on claims with a gold official figure (bound or ambiguous): {len(on_bound)}.",
          "", "| Claim | Lang | Gold label | Model figure | Gold official figure | Relative error |", "|---|---|---|---:|---:|---:|"]
    within5 = exact = 0
    for r in sorted(on_bound, key=lambda r: (r["claim_id"], r["lang"])):
        g = bind[r["claim_id"]]["official_figure"]
        err = (num(r["official_figure"]) - g) / g
        within5 += abs(err) <= 0.05
        exact += abs(err) < 1e-9
        L.append(f"| {r['claim_id']} | {r['lang']} | {r['label']} | {fmt(num(r['official_figure']))} | {fmt(g)} | {100 * err:+.1f}% |")
    echo = sum(1 for r in fig_rows if abs(num(r["official_figure"]) - claims[r["claim_id"]]["number"]) < 1e-9)
    L += ["", f"- Figure equal to the gold official figure: {rate(exact, len(on_bound))}; within 5%: {rate(within5, len(on_bound))}.",
          f"- Figure exactly equal to the number in the claim itself: {echo}/{len(fig_rows)} answers that gave a figure.",
          f"- Figures given for unbindable claims (no official figure was found by the binding study): "
          f"{sum(1 for r in fig_rows if r['label'] == 'unbindable')}.", ""]

    # 8. calibration
    L += ["## 8. Calibration (both languages)", "",
          "| Stated confidence | Answers | Mean confidence | Verdict correct | Of which CANNOT_VERIFY |", "|---|---:|---:|---|---:|"]
    calib = []
    for lo, hi in CONF_BINS:
        sub = [r for r in rows if num(r["confidence"]) is not None and lo <= num(r["confidence"]) < hi]
        if not sub:
            continue
        mean = sum(num(r["confidence"]) for r in sub) / len(sub)
        k = sum(r["correct"] for r in sub)
        calib.append((lo, hi, len(sub), mean, k))
        label = f"{lo:.2f}-{min(hi, 1):.2f}"
        L.append(f"| {label} | {len(sub)} | {mean:.2f} | {rate(k, len(sub))} | {sum(r['verdict'] == 'CANNOT_VERIFY' for r in sub)} |")
    for verdict_set, name in ((["CANNOT_VERIFY"], "CANNOT_VERIFY answers"), (["SUPPORTED", "CONTRADICTED"], "committed answers")):
        sub = [r for r in rows if r["verdict"] in verdict_set and num(r["confidence"]) is not None]
        if sub:
            L.append("")
            L.append(f"- {name}: mean stated confidence {sum(num(r['confidence']) for r in sub) / len(sub):.2f}; "
                     f"share correct {rate(sum(r['correct'] for r in sub), len(sub))}.")
    ece = sum(n * abs(m - k / n) for _, _, n, m, k in calib) / sum(n for _, _, n, _, _ in calib)
    L += [f"- Expected calibration error over these bins: {ece:.3f}.", ""]

    # 9. Hindi vs English
    both_right = sum(by[(i, "hi")]["correct"] and by[(i, "en")]["correct"] for i in ids)
    hi_only = sum(by[(i, "hi")]["correct"] and not by[(i, "en")]["correct"] for i in ids)
    en_only = sum(by[(i, "en")]["correct"] and not by[(i, "hi")]["correct"] for i in ids)
    both_wrong = len(ids) - both_right - hi_only - en_only
    same_verdict = sum(by[(i, "hi")]["verdict"] == by[(i, "en")]["verdict"] for i in ids)
    committed_hi = [i for i in ids if by[(i, "hi")]["verdict"] != "CANNOT_VERIFY"]
    committed_en = [i for i in ids if by[(i, "en")]["verdict"] != "CANNOT_VERIFY"]
    both_committed = sorted(set(committed_hi) & set(committed_en))
    L += ["## 9. Hindi versus English (paired by claim)", "",
          f"- Same verdict in both languages: {rate(same_verdict, len(ids))}.",
          f"- Correct in both: {both_right}; Hindi only: {hi_only}; English only: {en_only}; neither: {both_wrong}.",
          f"- Exact McNemar test on the {hi_only + en_only} discordant pairs: p = {mcnemar_exact(hi_only, en_only):.2f}.",
          f"- Committed (non-abstaining) answers: Hindi {len(committed_hi)} ({', '.join(committed_hi)}); "
          f"English {len(committed_en)} ({', '.join(committed_en)}); committed in both: {len(both_committed)} ({', '.join(both_committed) or 'none'}).", ""]

    fig = os.path.join(REPORT, "figures", "fig2_verifier_verdicts.svg")
    short = {"bound+match": "match", "bound+mismatch": "mismatch", "bound-ambiguous": "ambiguous", "unbindable": "unbindable"}
    panels = [(f"{LANG_NAME[lang]} wording of the claim",
               [(f"{short[lab]} (expect {EXPECTED[lab].replace('_', ' ').lower()})", conf[(lang, lab)]) for lab in LABELS])
              for lang in LANGS]
    size = svg_fig(fig, panels, f"{MODEL}, closed-book: verdicts by gold label ({len(claims)} claims)")
    png = svg_to_png(fig, size)
    L += ["## 10. Figure data", "",
          "Figure 2 (`report/figures/fig2_verifier_verdicts.svg`): verdict shares by gold label and language; counts as in section 2.", ""]
    with open(os.path.join(REPORT, "verifier_tables.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"wrote report/verifier_tables.md ({len(L)} lines), {os.path.relpath(fig, ROOT)}"
          + (f", {os.path.relpath(png, ROOT)}" if png else ""))


if __name__ == "__main__":
    main()

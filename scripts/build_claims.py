"""Build data/claims.jsonl from data/curation.jsonl (hand-selected clauses) and
data/candidates.jsonl (machine-extracted sentences).

Checks: every clause and num_raw must occur verbatim in the extracted sentence,
and the sentence must occur in the stored raw article text. Numbers are
normalised by parse_number() (a manual "value" is allowed only for number words
and is cross-checked to be present). Dedup rule (methodology.md): same scheme,
metric, geography and normalised number within 7 days -> keep earliest.
Usage: python -I scripts/build_claims.py"""
import html as H
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV = str.maketrans("०१२३४५६७८९", "0123456789")
MULT = {"करोड़": 1e7, "लाख": 1e5, "हजार": 1e3, "हज़ार": 1e3}
OUTLET = {"amarujala.com": "Amar Ujala", "patrika.com": "Patrika", "prabhatkhabar.com": "Prabhat Khabar",
          "aajtak.in": "Aaj Tak", "zeenews.india.com": "Zee News"}


def parse_number(raw):
    """Return (value, precision). '1 करोड़ 7 लाख 87 हजार 724' -> 10787724.
    '4.47 लाख करोड़' -> 4.47e12. precision = place value of last stated digit."""
    s = raw.translate(DEV).replace(",", "")
    toks = re.findall(r"\d+(?:\.\d+)?|करोड़|लाख|हज़ार|हजार|%|प्रतिशत|फीसदी", s)
    pairs, i = [], 0
    while i < len(toks):
        t = toks[i]
        if re.fullmatch(r"\d+(?:\.\d+)?", t):
            m, j = 1.0, i + 1
            while j < len(toks) and toks[j] in MULT:
                m *= MULT[toks[j]]
                j += 1
            pairs.append((float(t), m, len(t.split(".")[1]) if "." in t else 0))
            i = j
        else:
            i += 1
    if not pairs:
        return None, None
    # "18 हजार 690 करोड़" = (18 thousand + 690) crore: a smaller scale before a
    # final करोड़ scales the whole group by करोड़.
    if len(pairs) > 1 and pairs[-1][1] == MULT["करोड़"] and any(m < MULT["करोड़"] for _, m, _ in pairs[:-1]):
        inner = sum(n * m for n, m, _ in pairs[:-1]) + pairs[-1][0]
        return round(inner * MULT["करोड़"], 6), MULT["करोड़"] / (10 ** pairs[-1][2])
    total = sum(n * m for n, m, _ in pairs)
    prec = min(m / (10 ** d) for _, m, d in pairs)
    return round(total, 4), prec


def outlet_of(url):
    for k, v in OUTLET.items():
        if k in url:
            return v
    return "other"


def raw_text(path):
    raw = open(os.path.join(ROOT, path), encoding="utf-8", errors="ignore").read()
    raw = H.unescape(raw)
    try:
        raw += json.loads('"' + "".join(re.findall(r'"articleBody"\s*:\s*"((?:\\.|[^"\\])*)"', raw)) + '"')
    except Exception:
        pass
    return re.sub(r"\s+", " ", raw)


def main():
    cands = [json.loads(x) for x in open(os.path.join(ROOT, "data", "candidates.jsonl"), encoding="utf-8")]
    arts = {}
    for x in open(os.path.join(ROOT, "data", "articles_log.jsonl"), encoding="utf-8"):
        r = json.loads(x)
        arts[r["url"]] = r
    cur = [json.loads(x) for x in open(os.path.join(ROOT, "data", "curation.jsonl"), encoding="utf-8") if x.strip()]
    rows, errors = [], []
    for n, c in enumerate(cur, 1):
        cand = cands[c["cand"] - 1]
        sent = cand["sentence"]
        if c["clause"] not in sent:
            errors.append(f"curation line {n}: clause not in candidate {c['cand']}")
            continue
        if c["num_raw"] not in c["clause"]:
            errors.append(f"curation line {n}: num_raw not in clause")
            continue
        art = arts[cand["url"]]
        if re.sub(r"\s+", " ", c["clause"]) not in raw_text(art["raw_path"]):
            errors.append(f"curation line {n}: clause not found in raw HTML {art['raw_path']}")
            continue
        value, prec = parse_number(c["num_raw"])
        if "value" in c:
            value, prec = float(c["value"]), float(c.get("precision", 1000))
        if value is None:
            errors.append(f"curation line {n}: cannot parse number {c['num_raw']}")
            continue
        rows.append({
            "outlet": outlet_of(cand["url"]), "url": cand["url"], "pub_date": cand["pub_date"][:10],
            "headline": art.get("headline", ""), "raw_snapshot": art["raw_path"],
            "claim_text_hi": c["clause"], "english_gloss": c["gloss"], "scheme": c["scheme"],
            "number_raw": c["num_raw"], "number": value, "precision": prec, "hedge": c["hedge"],
            "unit": c["unit"], "metric": c["metric"], "geography": c["geo"],
            "time_reference": c["time_ref"], "speaker": c["speaker"], "candidate_line": c["cand"],
        })
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    rows.sort(key=lambda r: (r["pub_date"], r["candidate_line"]))
    kept, dups = [], []
    for r in rows:
        d = date.fromisoformat(r["pub_date"])
        twin = next((k for k in kept if k["scheme"] == r["scheme"] and k["metric"] == r["metric"]
                     and k["geography"] == r["geography"] and abs(k["number"] - r["number"]) < 1e-9
                     and (d - date.fromisoformat(k["pub_date"])).days <= 7), None)
        if twin:
            twin.setdefault("duplicates", []).append({"outlet": r["outlet"], "url": r["url"], "pub_date": r["pub_date"]})
            dups.append(r)
        else:
            kept.append(r)
    for i, r in enumerate(kept, 1):
        r["id"] = f"C{i:03d}"
    with open(os.path.join(ROOT, "data", "claims.jsonl"), "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps({"id": r.pop("id"), **r}, ensure_ascii=False) + "\n")
    print(f"curated {len(rows)}, duplicates dropped {len(dups)}, claims written {len(kept)}")


if __name__ == "__main__":
    main()

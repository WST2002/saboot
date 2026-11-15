"""Write report/tables.md and report/figures/*.svg. Every number the report uses
for the binding study is computed here from data/claims.jsonl,
data/bindings_verified.jsonl, data/pib_verification.jsonl and
data/articles_log.jsonl. Copy numbers into the report from tables.md only.
matplotlib is not installed, so the figures are written as plain SVG.
Usage: python -I scripts/report_tables.py"""
import json
import math
import os
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "report")
FIGURES = os.path.join(REPORT, "figures")
LABELS = ["bound+match", "bound+mismatch", "bound-ambiguous", "unbindable"]
BOUND = ("bound+match", "bound+mismatch")
WINDOW = ("2026-08-01", "2026-11-13")
OUTLET_CAP = 40
METHODOLOGY_OUTLETS = ["Amar Ujala", "Dainik Jagran", "Navbharat Times"]
COLORS = {"bound+match": "#2a78d6", "bound+mismatch": "#eb6834",
          "bound-ambiguous": "#1baf7a", "unbindable": "#eda100"}
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#d9d8d4", "#fcfcfb"


def load(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return centre - half, centre + half


def rate(k, n):
    if n == 0:
        return f"{k}/0 (no claims)"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% ({k}/{n}, 95% CI {100 * lo:.1f}-{100 * hi:.1f}%)"


def squash(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def quote_check(verif):
    """Search every recorded page quote in the page text saved from the browser.
    Returns (found, total, pages) or None when data/raw/pib_browser/ is absent (raw pages are not republished)."""
    folder = os.path.join(ROOT, "data", "raw", "pib_browser")
    if not os.path.isdir(folder):
        return None
    found = total = 0
    pages = set()
    for v in verif.values():
        for q in v["page_quotes"]:
            path = os.path.join(folder, f"{q['page']}.txt")
            total += 1
            pages.add(q["page"])
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    found += squash(q["quote"]) in squash(f.read())
    return found, total, len(pages)


def num(x):
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.2f}"


def geo_level(c):
    return "India" if c["geography"] == "India" else "State"


def speaker_group(c):
    return c["speaker"].split(" (")[0]


def lenient_label(b):
    if b["label"] == "bound+mismatch" and b["lenient_match"]:
        return "bound+match"
    return b["label"]


def label_table(title, key_fn, claims, bind):
    groups = defaultdict(Counter)
    for c in claims:
        groups[key_fn(c)][bind[c["id"]]["label"]] += 1
    order = sorted(groups, key=lambda g: (-sum(groups[g].values()), g))
    rows = [f"| {title} | " + " | ".join(LABELS) + " | total | coverage (any binding) | strict match rate |",
            "|---|" + "---:|" * (len(LABELS) + 3)]
    for g in order + ["All"]:
        cnt = sum(groups.values(), Counter()) if g == "All" else groups[g]
        n = sum(cnt.values())
        bound_any = n - cnt["unbindable"]
        strict = cnt["bound+match"] + cnt["bound+mismatch"]
        name = f"**{g}**" if g == "All" else g
        rows.append(f"| {name} | " + " | ".join(str(cnt[x]) for x in LABELS)
                    + f" | {n} | {rate(bound_any, n)} | {rate(cnt['bound+match'], strict) if strict else 'n/a'} |")
    return rows, order, groups


def svg_stacked(path, title, panels):
    """panels: list of (panel_title, [(row_name, Counter)]). Horizontal 100% stacked bars."""
    width, left, right, bar_h, gap = 720, 170, 60, 22, 10
    plot_w = width - left - right
    y = 56
    body = []
    for panel_title, rows in panels:
        body.append(f'<text x="{left}" y="{y}" font-size="13" font-weight="600" fill="{INK}">{escape(panel_title)}</text>')
        y += 12
        top = y
        for name, cnt in rows:
            n = sum(cnt.values())
            x = left
            segs = [(lab, cnt[lab]) for lab in LABELS if cnt[lab]]
            for i, (lab, k) in enumerate(segs):
                w = plot_w * k / n
                inner = w - (2 if i < len(segs) - 1 else 0)
                body.append(f'<rect x="{x:.1f}" y="{y}" width="{max(inner, 0.5):.1f}" height="{bar_h}" '
                            f'fill="{COLORS[lab]}"><title>{escape(name)}: {lab} {k}/{n}</title></rect>')
                if w >= 14:
                    body.append(f'<text x="{x + w / 2:.1f}" y="{y + 15}" font-size="11" text-anchor="middle" '
                                f'fill="{INK}">{k}</text>')
                x += w
            body.append(f'<text x="{left - 8}" y="{y + 15}" font-size="12" text-anchor="end" fill="{INK}">'
                        f'{escape(name)}</text>')
            body.append(f'<text x="{left + plot_w + 6}" y="{y + 15}" font-size="11" fill="{INK_2}">n={n}</text>')
            y += bar_h + gap
        for t in (0, 25, 50, 75, 100):
            gx = left + plot_w * t / 100
            body.insert(0, f'<line x1="{gx:.1f}" y1="{top - 4}" x2="{gx:.1f}" y2="{y - gap + 4}" stroke="{GRID}" stroke-width="1"/>')
            body.append(f'<text x="{gx:.1f}" y="{y + 8}" font-size="10" text-anchor="middle" fill="{INK_2}">{t}%</text>')
        y += 40
    legend_x = left
    for lab in LABELS:
        body.append(f'<rect x="{legend_x}" y="{y - 10}" width="12" height="12" rx="2" fill="{COLORS[lab]}"/>')
        body.append(f'<text x="{legend_x + 17}" y="{y}" font-size="12" fill="{INK}">{lab}</text>')
        legend_x += 30 + 7.2 * len(lab)
    height = y + 20
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
           f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
           f'<text x="{left}" y="28" font-size="15" font-weight="600" fill="{INK}">{escape(title)}</text>'] + body + ["</svg>"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))
    return width, height


def svg_to_png(svg_path, size):
    """PNG copy for the Google Doc, rendered by a local headless Edge or Chrome; skipped if neither exists."""
    browser = next((b for b in BROWSERS if os.path.exists(b)), None)
    if browser is None:
        return None
    png = svg_path[:-4] + ".png"
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    f"--window-size={size[0]},{size[1]}", f"--screenshot={png}", "file:///" + svg_path.replace(os.sep, "/")],
                   check=True, capture_output=True)
    return png


def main():
    claims = load("claims.jsonl")
    bind = {b["id"]: b for b in load("bindings_verified.jsonl")}
    verif = {v["id"]: v for v in load("pib_verification.jsonl")}
    arts = load("articles_log.jsonl")
    assert set(bind) == {c["id"] for c in claims}, "claims.jsonl and bindings_verified.jsonl ids differ: re-run merge_verification.py"
    n = len(claims)
    lab = Counter(bind[c["id"]]["label"] for c in claims)
    len_lab = Counter(lenient_label(bind[c["id"]]) for c in claims)
    strict_bound = lab["bound+match"] + lab["bound+mismatch"]
    any_bound = n - lab["unbindable"]
    lenient_matches = sum(1 for c in claims if bind[c["id"]]["label"] in BOUND and bind[c["id"]]["lenient_match"])

    fetched_ok = [a for a in arts if str(a["fetch_status"]) in ("200", "cached")]
    in_window = [a for a in fetched_ok if WINDOW[0] <= (a.get("pub_date") or "")[:10] <= WINDOW[1]]
    claim_urls = {c["url"] for c in claims} | {d["url"] for c in claims for d in c.get("duplicates", [])}
    with_claim = claim_urls & {a["url"] for a in in_window}
    dup_count = sum(len(c.get("duplicates", [])) for c in claims)
    outlets = Counter(c["outlet"] for c in claims)
    schemes = Counter(c["scheme"] for c in claims)
    over_cap = {o: k for o, k in outlets.items() if k > OUTLET_CAP}
    hedges = Counter(c["hedge"] for c in claims)

    bound_or_amb = [c["id"] for c in claims if bind[c["id"]]["label"] != "unbindable"]
    verified = [i for i in bound_or_amb if bind[i].get("verified")]
    in_verif_file = [i for i in bound_or_amb if i in verif]
    corrected = sorted(i for i in bind if bind[i].get("original"))
    label_changes = sorted(i for i in corrected if "label" in bind[i]["original"])
    date_fixes = sorted(i for i in corrected if "as_of_date" in bind[i]["original"])
    access = Counter(bind[i]["evidence_access"] for i in bound_or_amb)
    page_figure_ok = sum(1 for i in in_verif_file if verif[i]["figure_match"])
    page_date_ok = sum(1 for i in in_verif_file if verif[i]["date_match"])
    page_scope_ok = sum(1 for i in in_verif_file if verif[i]["scope_match"])
    quotes = quote_check(verif)
    amb_types = Counter(bind[c["id"]]["ambiguity_type"] for c in claims if bind[c["id"]]["label"] == "bound-ambiguous")
    amb_parts = Counter()
    for t, k in amb_types.items():
        for part in t.split(" and "):
            amb_parts["period gap" if part == "period" else part] += k

    geo = {g: [c for c in claims if geo_level(c) == g] for g in ("India", "State")}

    def cov(cs):
        return sum(1 for c in cs if bind[c["id"]]["label"] != "unbindable"), len(cs)

    def strict_cov(cs):
        return sum(1 for c in cs if bind[c["id"]]["label"] in BOUND), len(cs)

    L = ["# Saboot: report tables", "",
         "Generated by `scripts/report_tables.py` from `data/claims.jsonl`, `data/bindings_verified.jsonl`, "
         "`data/pib_verification.jsonl` and `data/articles_log.jsonl`. Do not edit by hand; re-run the script. "
         "Percentages carry Wilson 95% intervals. Labels follow the fixed rules in `data/labelling-rules.md`.", "",
         "## 1. Sample", "",
         f"- Articles attempted: {len(arts)}; fetched: {len(fetched_ok)}; failed: {len(arts) - len(fetched_ok)}.",
         f"- Fetched articles dated {WINDOW[0]} to {WINDOW[1]}: {len(in_window)}; of these with at least one kept or duplicate claim: {len(with_claim)}.",
         f"- Claims kept: {n}, from {len({c['url'] for c in claims})} articles, published {min(c['pub_date'] for c in claims)} "
         f"to {max(c['pub_date'] for c in claims)}; duplicates removed by the 7-day rule: {dup_count}.",
         "- Claims by scheme: " + ", ".join(f"{k} {v}" for k, v in schemes.most_common()) + ".",
         "- Claims by outlet: " + ", ".join(f"{k} {v}" for k, v in outlets.most_common()) + ".",
         f"- Outlets in the methodology: {', '.join(METHODOLOGY_OUTLETS)}. Outlets used: {', '.join(sorted(outlets))}. "
         f"Methodology outlets with claims: {', '.join(o for o in METHODOLOGY_OUTLETS if o in outlets) or 'none'}.",
         f"- Outlet cap {OUTLET_CAP}; outlets over the cap: " + (", ".join(f"{o} {k} (+{k - OUTLET_CAP})" for o, k in over_cap.items()) or "none") + ".",
         "- Claims by geography: " + ", ".join(f"{g} {len(cs)}" for g, cs in geo.items()) + ".",
         "- Claims by hedge: " + ", ".join(f"{k} {v}" for k, v in hedges.most_common()) + ".", "",
         "## 2. Label counts", "",
         "| Label | Strict rule | Lenient rule |", "|---|---:|---:|"]
    L += [f"| {x} | {lab[x]} | {len_lab[x]} |" for x in LABELS] + [f"| total | {n} | {sum(len_lab.values())} |", "",
          "The lenient rule only moves strict mismatches that fall within ±5% (±1 pp for percentages) to match; "
          "ambiguous and unbindable labels do not depend on the match rule.", "",
          "## 3. Headline rates", "",
          f"- Coverage, any binding (match + mismatch + ambiguous) / all: {rate(any_bound, n)}",
          f"- Strict coverage (match + mismatch) / all: {rate(strict_bound, n)}",
          f"- Ambiguous / all: {rate(lab['bound-ambiguous'], n)}",
          f"- Unbindable / all: {rate(lab['unbindable'], n)}",
          f"- Coverage, India-level claims: {rate(*cov(geo['India']))}",
          f"- Coverage, state-level claims: {rate(*cov(geo['State']))}",
          f"- Strict coverage, India-level claims: {rate(*strict_cov(geo['India']))}",
          f"- Strict coverage, state-level claims: {rate(*strict_cov(geo['State']))}",
          f"- Match rate among bound (strict rule): {rate(lab['bound+match'], strict_bound)}",
          f"- Match rate among bound (lenient rule): {rate(lenient_matches, strict_bound)}", "",
          "## 4. Official-page verification", "",
          f"- Bound or ambiguous claims: {len(bound_or_amb)}; with a browser verification record: {len(in_verif_file)}; "
          f"marked verified: {len(verified)}; unverified: {len(bound_or_amb) - len(verified)}.",
          f"- On the opened page: figure confirmed {page_figure_ok}/{len(in_verif_file)}, date as recorded {page_date_ok}/{len(in_verif_file)}, "
          f"scope confirmed {page_scope_ok}/{len(in_verif_file)}.",
          f"- Bindings corrected after verification: {len(corrected)} ({', '.join(corrected)}); "
          f"label changes: {len(label_changes)} ({', '.join(label_changes) or 'none'}); "
          f"as-of date corrections: {len(date_fixes)} ({', '.join(date_fixes) or 'none'}).",
          ("- Page quotes found verbatim in the saved page text: " + (f"{quotes[0]}/{quotes[1]} quotes from {quotes[2]} official pages."
           if quotes else "not checked (`data/raw/pib_browser/` is not present; raw pages are not republished).")),
          "- Evidence access for bound or ambiguous claims: " + ", ".join(f"{k} {v}" for k, v in access.most_common()) + ".", "",
          "## 5. Ambiguity reasons", "",
          "| Ambiguity type (as recorded) | Claims |", "|---|---:|"]
    L += [f"| {t} | {k} |" for t, k in amb_types.most_common()] + ["",
          "Counting each component of a combined type once: " + ", ".join(f"{k} {v}" for k, v in amb_parts.most_common()) + ".", ""]

    L += ["## 6. Labels by scheme (Table 1)", ""]
    rows, scheme_order, scheme_groups = label_table("Scheme", lambda c: c["scheme"], claims, bind)
    L += rows + ["", "## 7. Labels by outlet", ""]
    rows, _, _ = label_table("Outlet", lambda c: c["outlet"], claims, bind)
    L += rows + ["", "## 8. Labels by geography", ""]
    rows, geo_order, geo_groups = label_table("Geography", geo_level, claims, bind)
    L += rows + ["", "## 9. Labels by speaker", ""]
    rows, _, _ = label_table("Speaker", speaker_group, claims, bind)
    L += rows + [""]

    mism = sorted((c for c in claims if bind[c["id"]]["label"] == "bound+mismatch"),
                  key=lambda c: -abs(bind[c["id"]]["relative_gap"]))
    L += ["## 10. Strict mismatches (largest gap first)", "",
          "| Claim | Scheme | Outlet | Date | Claimed | Official (as of) | Gap | Lenient match | Note |",
          "|---|---|---|---|---|---|---:|---|---|"]
    for c in mism:
        b = bind[c["id"]]
        L.append(f"| {c['id']} | {c['scheme']} | {c['outlet']} | {c['pub_date']} | {c['number_raw']} = {num(c['number'])} | "
                 f"{num(b['official_figure'])} ({b['as_of_date']}) | {100 * b['relative_gap']:+.1f}% | {b['lenient_match']} | {b['reason']} |")
    L += [""]
    for c in mism:
        L += [f"- {c['id']} article: {c['url']}", f"- {c['id']} official: {bind[c['id']]['bound_official_url']}"]
    L += [""]

    near = sorted((c for c in claims if bind[c["id"]]["label"] == "bound-ambiguous" and bind[c["id"]]["strict_match"] is False),
                  key=lambda c: -abs(bind[c["id"]]["relative_gap"]))
    L += ["## 11. Ambiguous claims whose number differs from the nearest official figure", "",
          f"{len(near)} of {lab['bound-ambiguous']} ambiguous claims would fail the strict rule against the nearest official figure; "
          "they are not counted as mismatches because the period or definition differs.", "",
          "| Claim | Scheme | Outlet | Date | Claimed | Official (as of) | Gap | Ambiguity | Reason |",
          "|---|---|---|---|---|---|---:|---|---|"]
    for c in near:
        b = bind[c["id"]]
        L.append(f"| {c['id']} | {c['scheme']} | {c['outlet']} | {c['pub_date']} | {c['number_raw']} | "
                 f"{num(b['official_figure'])} ({b['as_of_date']}) | {100 * b['relative_gap']:+.1f}% | {b['ambiguity_type']} | {b['reason']} |")
    L += [""]
    for c in near:
        L += [f"- {c['id']} article: {c['url']}", f"- {c['id']} official: {bind[c['id']]['bound_official_url']}"]
    L += [""]

    L += ["## 12. Figure data", "",
          "Figure 1 (`report/figures/fig1_labels_by_scheme_geography.svg`): share of claims per label, by scheme "
          "(top panel) and by geography (bottom panel); counts as in sections 6 and 8.", "",
          ""]

    os.makedirs(FIGURES, exist_ok=True)
    fig1 = os.path.join(FIGURES, "fig1_labels_by_scheme_geography.svg")
    size = svg_stacked(fig1,
                f"Binding labels for {n} numerical claims (strict rule)",
                [("By scheme", [(s, scheme_groups[s]) for s in scheme_order]),
                 ("By geography", [(g, geo_groups[g]) for g in geo_order])])
    png = svg_to_png(fig1, size)
    with open(os.path.join(REPORT, "tables.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"wrote report/tables.md ({len(L)} lines), {os.path.relpath(fig1, ROOT)}"
          + (f", {os.path.relpath(png, ROOT)}" if png else " (no PNG: Edge/Chrome not found)"))


if __name__ == "__main__":
    main()

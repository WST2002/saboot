"""Score the evidence-given LLM-verifier condition (methodology.md sections 4-5, condition C2).

Reads data/evidence_results.jsonl (scripts/run_evidence.py), data/evidence_excerpts.jsonl, data/claims.jsonl,
data/bindings_verified.jsonl and, for the comparison, the closed-book answers in data/verifier_results.jsonl.
Writes report/evidence_tables.md. Every model is scored on the answers it gave; a model whose run did not
finish (gemini-3.8-flash may be overloaded) is marked PARTIAL with its answered/planned counts, and its
comparisons use only the claims it answered.

Gold label for each claim (fixed before any model call): bound+match -> MATCH, bound+mismatch -> MISMATCH,
bound-ambiguous -> AMBIGUOUS, unbindable (near-miss excerpt) -> CANNOT_VERIFY. For the comparison with the
closed-book run both conditions are put on the closed-book scale: MATCH -> SUPPORTED, MISMATCH -> CONTRADICTED,
AMBIGUOUS and CANNOT_VERIFY -> CANNOT_VERIFY, scored against the closed-book expectation for the label.
Figure: the model's official_figure against the gold official figure (exact, within 1%). Date: the model's
as_of_date against the gold as-of date (exact, same month). Quote: the model's evidence_quote appears in the
excerpt (whitespace-insensitive).
--results and --out let the scorer run on the mock file written by `run_evidence.py --dry-run`; output from
mock rows is headed MOCK and must not be reported.
Usage: python -I -X utf8 scripts/score_evidence.py [--results path] [--out path]"""
import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report_tables import svg_to_png, wilson  # noqa: E402
from score_verifier import EXPECTED, mcnemar_exact, num, svg_fig  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
LANGS = ("hi", "en")
LANG_NAME = {"hi": "Hindi", "en": "English"}
GOLD_LABELS = ["bound+match", "bound+mismatch", "bound-ambiguous", "unbindable"]
LABELS = ["MATCH", "MISMATCH", "AMBIGUOUS", "CANNOT_VERIFY"]
GOLD = {"bound+match": "MATCH", "bound+mismatch": "MISMATCH", "bound-ambiguous": "AMBIGUOUS", "unbindable": "CANNOT_VERIFY"}
TO_CLOSED = {"MATCH": "SUPPORTED", "MISMATCH": "CONTRADICTED", "AMBIGUOUS": "CANNOT_VERIFY", "CANNOT_VERIFY": "CANNOT_VERIFY"}
FIG_CATS = ["MATCH", "MISMATCH", "AMBIGUOUS", "CANNOT_VERIFY"]  # closed-book SUPPORTED/CONTRADICTED shown as MATCH/MISMATCH
FIG_COLORS = ["#2a78d6", "#eb6834", "#7d4fc4", "#9a9893"]
FIG = os.path.join(ROOT, "report", "figures", "fig2_closed_vs_evidence.svg")


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def rate(k, n):
    if n == 0:
        return "n/a (0)"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% ({k}/{n}, 95% CI {100 * lo:.1f}-{100 * hi:.1f}%)"


def flat(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()


def section_model(model, rows, excerpts, binds, claims, closed, fig_path=None):
    planned = 2 * sum(1 for e in excerpts.values() if e["evidence_block"])
    status = rows[0]["model_status"]
    tag = "" if status == "complete" else " - PARTIAL"
    L = [f"## {model}{tag}", "",
         f"- Answers: {len(rows)} of {planned} planned; run status: {status}; unparsed: {sum(not r['parsed'] for r in rows)}; "
         f"claims answered: {len({r['claim_id'] for r in rows})}.", ""]
    for r in rows:
        r["gold"] = GOLD[r["gold_label"]]
        r["correct"] = r["label"] == r["gold"]

    L += ["### Label by gold label (rows gold, columns model)", "",
          "| Language | Gold label | n | " + " | ".join(LABELS) + " | other/unparsed |", "|---|---|---:|" + "---:|" * (len(LABELS) + 1)]
    for lang in LANGS:
        for g in GOLD_LABELS:
            sub = [r for r in rows if r["lang"] == lang and r["gold_label"] == g]
            cnt = Counter(r["label"] for r in sub)
            other = len(sub) - sum(cnt[x] for x in LABELS)
            L.append(f"| {LANG_NAME[lang]} | {g} | {len(sub)} | " + " | ".join(str(cnt[x]) for x in LABELS) + f" | {other} |")
    L += [""]

    L += ["### Agreement with the gold labels", ""]
    for lang in LANGS + ("both",):
        rs = [r for r in rows if lang == "both" or r["lang"] == lang]
        L.append(f"- {'Both languages' if lang == 'both' else LANG_NAME[lang]}: {rate(sum(r['correct'] for r in rs), len(rs))}")
        for g in GOLD_LABELS:
            sub = [r for r in rs if r["gold_label"] == g]
            L.append(f"  - {g} (expected {GOLD[g]}): {rate(sum(r['correct'] for r in sub), len(sub))}")
    cv = sum(r["gold"] == "CANNOT_VERIFY" for r in rows)
    L += [f"- Baseline that always answers CANNOT_VERIFY: {rate(cv, len(rows))}.",
          f"- Baseline that answers MATCH on every bound or ambiguous claim and CANNOT_VERIFY on the rest: "
          f"{rate(sum(r['gold'] in ('MATCH', 'CANNOT_VERIFY') for r in rows), len(rows))}.", ""]

    bound = [r for r in rows if r["kind"] == "bound"]
    with_fig = [r for r in bound if num(r["official_figure"]) is not None and binds[r["claim_id"]]["official_figure"]]
    exact = sum(abs(num(r["official_figure"]) - binds[r["claim_id"]]["official_figure"]) <= 1e-9 * binds[r["claim_id"]]["official_figure"] for r in with_fig)
    close = sum(abs(num(r["official_figure"]) - binds[r["claim_id"]]["official_figure"]) <= 0.01 * binds[r["claim_id"]]["official_figure"] for r in with_fig)
    echo = sum(abs(num(r["official_figure"]) - claims[r["claim_id"]]["number"]) < 1e-9 for r in with_fig)
    dated = [r for r in bound if r["as_of_date"]]
    d_exact = sum(r["as_of_date"] == binds[r["claim_id"]]["as_of_date"] for r in dated)
    d_month = sum((r["as_of_date"] or "")[:7] == (binds[r["claim_id"]]["as_of_date"] or "")[:7] for r in dated)
    quoted = [r for r in rows if r["evidence_quote"]]
    in_ex = sum(flat(r["evidence_quote"]) in flat(excerpts[r["claim_id"]]["evidence_block"]) for r in quoted)
    L += ["### Figure and date it relied on (bound and ambiguous claims)", "",
          f"- Answers giving a figure: {len(with_fig)}/{len(bound)}; equal to the gold official figure: {rate(exact, len(with_fig))}; "
          f"within 1%: {rate(close, len(with_fig))}; equal to the claim's own number instead: {echo}.",
          f"- Answers giving a date: {len(dated)}/{len(bound)}; equal to the gold as-of date: {rate(d_exact, len(dated))}; "
          f"same month: {rate(d_month, len(dated))}.",
          f"- Evidence quotes found verbatim in the excerpt (all answers with a quote): {rate(in_ex, len(quoted))}.",
          "- Gold figure for ambiguous claims with conflicting official figures is the one recorded in the binding; "
          "the other figure on the excerpt counts as a miss here.", ""]

    near = [r for r in rows if r["kind"] == "near_miss"]
    flagged = {cid for cid, e in excerpts.items() if e["kind"] == "near_miss" and e["selection"].get("related_figures")}
    L += ["### Near-miss excerpts (unbindable claims; the excerpt does not contain the claim's number)", "",
          f"- Answers: {len(near)}; CANNOT_VERIFY (right): {rate(sum(r['label'] == 'CANNOT_VERIFY' for r in near), len(near))}.",
          f"- False MATCH: {rate(sum(r['label'] == 'MATCH' for r in near), len(near))}; MISMATCH: "
          f"{rate(sum(r['label'] == 'MISMATCH' for r in near), len(near))}; AMBIGUOUS: {rate(sum(r['label'] == 'AMBIGUOUS' for r in near), len(near))}."]
    for lang in LANGS:
        sub = [r for r in near if r["lang"] == lang]
        L.append(f"  - {LANG_NAME[lang]}: false MATCH {rate(sum(r['label'] == 'MATCH' for r in sub), len(sub))}")
    fl = [r for r in near if r["claim_id"] in flagged]
    L += [f"- On excerpts holding a number within 25% of the claim ({len(flagged)} claims, flagged for review before the run): "
          f"false MATCH {rate(sum(r['label'] == 'MATCH' for r in fl), len(fl))}, any commitment (MATCH or MISMATCH) "
          f"{rate(sum(r['label'] in ('MATCH', 'MISMATCH') for r in fl), len(fl))}.", ""]
    false_match = sorted(r for r in ((r["claim_id"], r["lang"], r["official_figure"], r["evidence_quote"]) for r in near if r["label"] == "MATCH"))
    if false_match:
        L += ["| Claim | Lang | Model figure | Model quote |", "|---|---|---|---|"]
        L += [f"| {c} | {lang} | {f} | {(q or '-').replace('|', '/')[:120]} |" for c, lang, f, q in false_match] + [""]

    by = {(r["claim_id"], r["lang"]): r for r in rows}
    ids = sorted({r["claim_id"] for r in rows if (r["claim_id"], "hi") in by and (r["claim_id"], "en") in by})
    same = sum(by[(i, "hi")]["label"] == by[(i, "en")]["label"] for i in ids)
    hi_only = sum(by[(i, "hi")]["correct"] and not by[(i, "en")]["correct"] for i in ids)
    en_only = sum(by[(i, "en")]["correct"] and not by[(i, "hi")]["correct"] for i in ids)
    L += ["### Hindi versus English (paired by claim)", "",
          f"- Claims answered in both languages: {len(ids)}; same label: {rate(same, len(ids))}.",
          f"- Correct in Hindi only: {hi_only}; English only: {en_only}; exact McNemar p = {mcnemar_exact(hi_only, en_only):.2f}.", ""]

    cb = {(r["claim_id"], r["lang"]): r for r in closed if r["model"] == model}
    pairs = [(r, cb[(r["claim_id"], r["lang"])]) for r in rows if (r["claim_id"], r["lang"]) in cb]
    L += ["### Compared with the closed-book run (same model, claim and language)", ""]
    if not pairs:
        L += [f"- No closed-book answers from {model} for these claims; no comparison.", ""]
        return L
    for e, c in pairs:
        exp = EXPECTED[e["gold_label"]]
        e["cb_scale_correct"] = TO_CLOSED.get(e["label"]) == exp
        c["cb_correct"] = c["verdict"] == exp
    b = sum(c["cb_correct"] and not e["cb_scale_correct"] for e, c in pairs)
    k = sum(e["cb_scale_correct"] and not c["cb_correct"] for e, c in pairs)
    L += [f"- Paired answers: {len(pairs)}. Correct on the closed-book scale: closed-book {rate(sum(c['cb_correct'] for _, c in pairs), len(pairs))}; "
          f"evidence-given {rate(sum(e['cb_scale_correct'] for e, _ in pairs), len(pairs))}.",
          f"- Right only closed-book: {b}; right only with evidence: {k}; exact McNemar p = {mcnemar_exact(b, k):.2f}.", "",
          "| Gold label | n | Closed-book correct | Evidence-given correct (closed-book scale) | Evidence-given correct (4 labels) |",
          "|---|---:|---|---|---|"]
    for g in GOLD_LABELS:
        sub = [(e, c) for e, c in pairs if e["gold_label"] == g]
        L.append(f"| {g} | {len(sub)} | {rate(sum(c['cb_correct'] for _, c in sub), len(sub))} | "
                 f"{rate(sum(e['cb_scale_correct'] for e, _ in sub), len(sub))} | {rate(sum(e['correct'] for e, _ in sub), len(sub))} |")
    bindable = [(e, c) for e, c in pairs if e["gold_label"] in ("bound+match", "bound+mismatch")]
    L += ["", f"- False abstention on cleanly bound claims (CANNOT_VERIFY or AMBIGUOUS where MATCH/MISMATCH was right): closed-book "
          f"{rate(sum(c['verdict'] == 'CANNOT_VERIFY' for _, c in bindable), len(bindable))}; evidence-given "
          f"{rate(sum(e['label'] in ('CANNOT_VERIFY', 'AMBIGUOUS') for e, _ in bindable), len(bindable))}.", ""]
    if fig_path:
        L += figure(model, pairs, fig_path)
    return L


def figure(model, pairs, path):
    """Closed-book against evidence-given answers by gold label, both languages pooled, on the paired answers."""
    cb_name = {"SUPPORTED": FIG_CATS[0], "CONTRADICTED": FIG_CATS[1], "CANNOT_VERIFY": FIG_CATS[3]}
    ev_name = dict(zip(LABELS, FIG_CATS))
    rows = {"Closed-book": {}, "Evidence-given": {}}
    for g in GOLD_LABELS:
        sub = [(e, c) for e, c in pairs if e["gold_label"] == g]
        rows["Closed-book"][g] = Counter(cb_name[c["verdict"]] for _, c in sub)
        rows["Evidence-given"][g] = Counter(ev_name[e["label"]] for e, _ in sub)
    names = {"bound+match": "match", "bound+mismatch": "mismatch", "bound-ambiguous": "ambiguous", "unbindable": "unbindable"}
    expect = {"Closed-book": EXPECTED, "Evidence-given": GOLD}
    titles = {"Closed-book": "Closed-book: no evidence in the prompt",
              "Evidence-given": "Evidence-given: official excerpt in the prompt"}
    panels = [(titles[cond], [(f"{names[g]} (expect {expect[cond][g].replace('_', ' ').lower()})", rows[cond][g]) for g in GOLD_LABELS])
              for cond in rows]
    size = svg_fig(path, panels, f"{model}: answers by gold label (Hindi and English, {len(pairs)} per condition)",
                   cats=FIG_CATS, colors=dict(zip(FIG_CATS, FIG_COLORS)), legend="Model answer:")
    png = svg_to_png(path, size)
    L = ["### Figure data (closed-book against evidence-given, both languages)", "",
         f"Figure 2 (`{os.path.relpath(png or path, ROOT).replace(os.sep, '/')}`); paired answers only.", "",
         "| Condition | Gold label | n | " + " | ".join(FIG_CATS) + " |", "|---|---|---:|" + "---:|" * len(FIG_CATS)]
    for cond in rows:
        for g in GOLD_LABELS:
            cnt = rows[cond][g]
            L.append(f"| {cond} | {g} | {sum(cnt.values())} | " + " | ".join(str(cnt[x]) for x in FIG_CATS) + " |")
    return L + [""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(DATA, "evidence_results.jsonl"))
    ap.add_argument("--out", default=os.path.join(ROOT, "report", "evidence_tables.md"))
    args = ap.parse_args()
    rows = load(args.results)
    if not rows:
        raise SystemExit(f"{args.results} is empty: run scripts/run_evidence.py first")
    mock = any(r.get("mock") for r in rows)
    if mock and os.path.abspath(args.out).startswith(os.path.join(ROOT, "report")):
        raise SystemExit("mock results cannot be written under report/: pass --out data/prompts_preview/<file>.md")
    excerpts = {r["claim_id"]: r for r in load(os.path.join(DATA, "evidence_excerpts.jsonl"))}
    stale = [r["claim_id"] for r in rows if r["evidence_sha256"] != excerpts[r["claim_id"]]["evidence_sha256"]]
    if stale:
        raise SystemExit(f"answers made with a different excerpt than the frozen one: {sorted(set(stale))}")
    binds = {b["id"]: b for b in load(os.path.join(DATA, "bindings_verified.jsonl"))}
    claims = {c["id"]: c for c in load(os.path.join(DATA, "claims.jsonl"))}
    closed = load(os.path.join(DATA, "verifier_results.jsonl"))
    kinds = Counter(e["kind"] for e in excerpts.values())
    L = (["# MOCK RESULTS: NOT REAL MODEL ANSWERS, DO NOT REPORT", ""] if mock else []) + [
        "# Saboot: evidence-given verifier tables (condition C2)", "",
        "Generated by `scripts/score_evidence.py` from `" + os.path.relpath(args.results, ROOT).replace(os.sep, "/") +
        "`, `data/evidence_excerpts.jsonl`, `data/bindings_verified.jsonl`, `data/claims.jsonl` and `data/verifier_results.jsonl`. "
        "Do not edit by hand. Percentages carry Wilson 95% intervals.", "",
        f"- Excerpts (frozen before any call): bound or ambiguous {kinds['bound']}, near-miss {kinds['near_miss']}, "
        f"no excerpt (not sent) {kinds['none']}.",
        "- Gold label for each claim: " + ", ".join(f"{k} -> {v}" for k, v in GOLD.items()) + ".", ""]
    for model in sorted({r["model"] for r in rows}):
        L += section_model(model, [r for r in rows if r["model"] == model], excerpts, binds, claims, closed, None if mock else FIG)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"wrote {os.path.relpath(args.out, ROOT)} ({len(L)} lines){' - MOCK' if mock else ''}")


if __name__ == "__main__":
    main()

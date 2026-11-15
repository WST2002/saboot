"""Run the evidence-given LLM-verifier condition (paper Section 3.4, condition C2).

Each claim with a frozen excerpt in data/evidence_excerpts.jsonl (built beforehand by
scripts/build_evidence_excerpts.py; 46 bound or ambiguous claims with the excerpt they were bound to,
unbindable claims with a near-miss excerpt from the closest official page checked) is sent to each model
twice: once with the Hindi clause and once with the English gloss. Instructions and evidence are the same
in both; only the claim text and the figure to check change language. The model labels the claim MATCH,
MISMATCH, AMBIGUOUS or CANNOT_VERIFY from the evidence alone and gives the official figure, its date and
the evidence phrase it relied on.

Same rules as scripts/run_verifier.py (shared code): free tier only, fixed pause per model, backoff on
per-minute 429s, full stop (partial results kept) on billing, payment, daily-quota or exhausted-quota errors;
a model that stays overloaded (HTTP 5xx) after all retries stops alone and its partial answers are kept
and marked (gemini-3.8-flash was overloaded on 14 Nov 2026). Raw responses are cached under
data/llm_raw_evidence/<model>/ keyed by claim, language and prompt hash, so nothing runs twice. Each run
appends the per-model outcome to data/llm_raw_evidence/run_log.jsonl. The key is read from .env and sent
only in the x-goog-api-key header; it is never printed.

--dry-run reads no key and makes no call: it writes the exact prompts to data/prompts_preview/evidence/,
prints how many calls a run would make, and writes a MOCK results file
(data/prompts_preview/mock_evidence_results.jsonl, every row marked "mock": true; gemini-3.8-flash answers
only 20 claims to imitate a partial run) so scripts/score_evidence.py can be checked end to end.
Usage: python -I -X utf8 scripts/run_evidence.py [--models m1,m2] [--limit N] [--dry-run | --parse-only]"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_verifier import (LANGS, MODELS, SCHEME_NAMES, parse_answer, parse_models, preview,  # noqa: E402
                          prompt_hash, read_key, run_models)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "llm_raw_evidence")
RUN_LOG = os.path.join(RAW, "run_log.jsonl")
EXCERPTS = os.path.join(DATA, "evidence_excerpts.jsonl")
RESULTS = os.path.join(DATA, "evidence_results.jsonl")
PREVIEW = os.path.join(DATA, "prompts_preview")
LABELS = ("MATCH", "MISMATCH", "AMBIGUOUS", "CANNOT_VERIFY")
GOLD = {"bound+match": "MATCH", "bound+mismatch": "MISMATCH", "bound-ambiguous": "AMBIGUOUS", "unbindable": "CANNOT_VERIFY"}
HEDGE_EN = {"over": "more than ", "about": "about ", "none": ""}
PROMPT = """You check a numerical claim about an Indian government scheme against an excerpt from official pages.
Use only the evidence below. Do not use outside knowledge.
SCHEME: {scheme}
CLAIM: {claim}
FIGURE TO CHECK: {figure}
ARTICLE DATE: {date}
EVIDENCE:
{evidence}

Labels:
MATCH: the evidence states a figure for the same metric, place and period, and it agrees with the claim at the precision the claim states ("more than X" agrees if the official figure is at least X; "about X" agrees within 5%).
MISMATCH: the evidence states a figure for the same metric, place and period, and it does not agree.
AMBIGUOUS: the evidence states a figure for this or a closely related metric, but it cannot settle the claim: a different definition or scope, a date more than about one month from the time the claim refers to, several official figures that disagree, or an official figure too imprecise to test the claim.
CANNOT_VERIFY: the evidence does not state a figure for this metric and place.
Answer in JSON only, with exactly these keys:
{{"label": "MATCH" | "MISMATCH" | "AMBIGUOUS" | "CANNOT_VERIFY",
 "official_figure": <the official figure from the evidence you compared with the claim, as a plain number in the claim's unit, fully written out (for example 94900000, not "9.49 crore"; a percentage as 82.09), or null>,
 "as_of_date": <the date that official figure refers to, YYYY-MM-DD, or null>,
 "evidence_quote": <the shortest exact phrase from the evidence that states that figure, or null>,
 "confidence": <number from 0 to 1: how likely your label is correct>,
 "reason": <one sentence>}}"""


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_excerpts():
    """Frozen excerpts; fails fast if any evidence block no longer matches its recorded hash."""
    if not os.path.exists(EXCERPTS):
        raise SystemExit("data/evidence_excerpts.jsonl missing: run scripts/build_evidence_excerpts.py first")
    rows = {r["claim_id"]: r for r in load("evidence_excerpts.jsonl")}
    bad = [cid for cid, r in rows.items() if r["evidence_block"] and sha(r["evidence_block"]) != r["evidence_sha256"]]
    if bad:
        raise SystemExit(f"evidence blocks changed after freezing: {bad}: restore data/evidence_excerpts.jsonl from git")
    return rows


def short_number(x):
    """Indian-unit English form of x, kept exact (falls back to digit grouping)."""
    for unit, word in ((1e12, "lakh crore"), (1e7, "crore"), (1e5, "lakh")):
        if x >= unit and round(x / unit, 4) == x / unit:
            return f"{x / unit:,.4f}".rstrip("0").rstrip(".") + " " + word
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:g}"


def figure_text(claim, lang):
    if lang == "hi":
        return claim["number_raw"]
    x, unit = claim["number"], claim["unit"]
    if unit == "percent":
        body = f"{x:g}%"
    elif unit == "rupees":
        body = f"Rs {short_number(x)}"
    else:
        body = f"{short_number(x)} {unit}"
    return HEDGE_EN[claim["hedge"]] + body


def build_prompt(claim, excerpt, lang):
    text = claim["claim_text_hi"] if lang == "hi" else claim["english_gloss"]
    return PROMPT.format(scheme=SCHEME_NAMES[claim["scheme"]], claim=text, figure=figure_text(claim, lang),
                         date=claim["pub_date"], evidence=excerpt["evidence_block"])


def cache_path(model, cid, lang, phash):
    return os.path.join(RAW, model, f"{cid}_{lang}_{phash}.json")


def evidence_jobs(model, claims, excerpts):
    jobs = []
    for c in claims:
        ex = excerpts[c["id"]]
        if not ex["evidence_block"]:
            continue
        for lang in LANGS:
            prompt = build_prompt(c, ex, lang)
            jobs.append((cache_path(model, c["id"], lang, prompt_hash(model, prompt)),
                         {"claim_id": c["id"], "lang": lang, "evidence_sha256": ex["evidence_sha256"]}, prompt))
    return jobs


def last_status():
    status = {}
    if os.path.exists(RUN_LOG):
        with open(RUN_LOG, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    status[r["model"]] = r["status"]
    return status


def result_row(model, job, ex, rec, answer, text, status):
    ans = answer or {}
    label = str(ans.get("label") or "").upper().strip().replace(" ", "_") or None
    return {"model": model, "model_version": rec.get("model_version"), "claim_id": job[1]["claim_id"],
            "lang": job[1]["lang"], "kind": ex["kind"], "gold_label": ex["gold_label"],
            "evidence_sha256": ex["evidence_sha256"], "prompt_hash": rec.get("prompt_hash"),
            "called_at": rec.get("called_at"), "parsed": bool(ans), "label": label,
            "official_figure": ans.get("official_figure"), "as_of_date": ans.get("as_of_date"),
            "evidence_quote": ans.get("evidence_quote"), "confidence": ans.get("confidence"),
            "reason": ans.get("reason"), "raw_text": None if ans else text, "model_status": status}


def write_results(jobs_by_model, excerpts):
    status = last_status()
    rows = []
    for model, jobs in jobs_by_model.items():
        answered = [j for j in jobs if os.path.exists(j[0])]
        state = "complete" if len(answered) == len(jobs) else f"partial ({len(answered)}/{len(jobs)}; last run: {status.get(model, 'not run')})"
        for job in answered:
            with open(job[0], encoding="utf-8") as f:
                rec = json.load(f)
            rec["model_version"] = rec["response"].get("modelVersion")
            answer, text = parse_answer(rec["response"])
            rows.append(result_row(model, job, excerpts[job[1]["claim_id"]], rec, answer, text, state))
    with open(RESULTS, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def write_mock(jobs_by_model, excerpts, binds):
    """Fake answers for checking the scorer only; never mixed with real results."""
    rows = []
    for model, jobs in jobs_by_model.items():
        keep = jobs if model != "gemini-3.8-flash" else [j for j in jobs if j[1]["claim_id"] in
                                                         sorted({k[1]["claim_id"] for k in jobs})[:20]]
        state = "complete" if len(keep) == len(jobs) else f"partial ({len(keep)}/{len(jobs)}; MOCK)"
        for job in keep:
            cid, lang = job[1]["claim_id"], job[1]["lang"]
            b, ex = binds[cid], excerpts[cid]
            pick = int(sha(model + cid + lang), 16) % 4
            label = GOLD[b["label"]] if pick else LABELS[int(sha(cid), 16) % 4]
            answer = {"label": label, "official_figure": b["official_figure"] if label != "CANNOT_VERIFY" else None,
                      "as_of_date": b["as_of_date"] if label != "CANNOT_VERIFY" else None,
                      "evidence_quote": None, "confidence": 0.5 + pick / 8, "reason": "MOCK answer"}
            rec = {"prompt_hash": prompt_hash(model, job[2]), "called_at": "MOCK", "model_version": "MOCK"}
            row = result_row(model, job, ex, rec, answer, "", state)
            row["mock"] = True
            rows.append(row)
    path = os.path.join(PREVIEW, "mock_evidence_results.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only the first N claims")
    ap.add_argument("--models", help=f"comma-separated subset of: {', '.join(MODELS)} (default: all)")
    ap.add_argument("--parse-only", action="store_true", help="rebuild data/evidence_results.jsonl from the cache")
    ap.add_argument("--dry-run", action="store_true", help="write prompts + a mock results file under data/prompts_preview/ and exit")
    args = ap.parse_args()
    models = parse_models(args.models)
    claims = load("claims.jsonl")
    if args.limit:
        claims = claims[:args.limit]
    excerpts = load_excerpts()
    jobs = {m: evidence_jobs(m, claims, excerpts) for m in models}
    if args.dry_run:
        for m, (cached, todo) in preview(jobs, os.path.join(PREVIEW, "evidence")).items():
            print(f"[{m}] prompts: {cached + todo}; cached (no call): {cached}; calls a run would make: {todo}")
        binds = {b["id"]: b for b in load("bindings_verified.jsonl")}
        n = write_mock(jobs, excerpts, binds)
        print(f"prompts written to data/prompts_preview/evidence/; mock results ({n} rows, MOCK) -> "
              "data/prompts_preview/mock_evidence_results.jsonl; no key read, no call made")
        return
    stopped = False
    if not args.parse_only:
        counts, status, stopped = run_models(models, jobs, read_key())
        os.makedirs(RAW, exist_ok=True)
        with open(RUN_LOG, "a", encoding="utf-8") as f:
            for m in models:
                f.write(json.dumps({"run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "model": m,
                                    "new_calls": counts[m], "status": status.get(m, "not started")}) + "\n")
        print(f"new calls this run: {counts}; status: {status}")
    all_jobs = {m: evidence_jobs(m, claims, excerpts) for m in MODELS}
    print(f"results rows: {write_results(all_jobs, excerpts)} -> data/evidence_results.jsonl")
    if stopped:
        sys.exit(2)


if __name__ == "__main__":
    main()

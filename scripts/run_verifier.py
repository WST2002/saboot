"""Run the closed-book LLM-verifier experiment (methodology.md section 4, condition C1).

Each of the 102 claims is sent to each model twice: once with the original Hindi
clause and once with its English gloss. The instructions are the same English
text in both cases; only the claim text changes. Every raw response is cached
under data/llm_raw/<model>/ keyed by claim id, language and prompt hash, so a
rerun never repeats a call that already succeeded. Parsed answers are written to
data/verifier_results.jsonl.

Models: gemini-2.5-flash and gemini-2.5-flash-lite (the planned pair) returned HTTP 404
"no longer available to new users" on 2026-11-14; the API named these replacements,
and the owner approved them. Free tier only: two models,a fixed pause between calls (below the free per-minute
limits), backoff on per-minute 429s, and a full stop (partial results kept) on any
error that mentions billing, payment, a daily quota or an exhausted quota.
The API key is read from .env and sent only in the x-goog-api-key header.
Usage: python -I scripts/run_verifier.py [--limit N]"""
import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "llm_raw")
RESULTS = os.path.join(ROOT, "data", "verifier_results.jsonl")
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
# seconds between calls: flash <= 10/min and flash-lite <= 15/min on the free tier
MODELS = {"gemini-3.8-flash": 6.5, "gemini-3.5-flash-lite": 4.5}
LANGS = ("hi", "en")
SCHEME_NAMES = {
    "PM-KISAN": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
    "PM-JAY": "Ayushman Bharat PM-JAY (Pradhan Mantri Jan Arogya Yojana)",
    "JJM": "Jal Jeevan Mission (JJM)",
    "PMAY": "Pradhan Mantri Awas Yojana (PMAY, Gramin and Urban)",
    "MGNREGA/VB-G RAM G": "MGNREGA (rural employment guarantee scheme)",
    "PMUY": "Pradhan Mantri Ujjwala Yojana (PMUY)",
}
PROMPT = """You check numerical claims about Indian government schemes against official statistics.
SCHEME: {scheme}
CLAIM: {claim}
ARTICLE DATE: {date}
Answer in JSON only, with exactly these keys:
{{"verdict": "SUPPORTED" | "CONTRADICTED" | "CANNOT_VERIFY",
 "source_title": <title of the official source you rely on, or null>,
 "source_url": <official URL you rely on, or null>,
 "official_figure": <the official number as a plain number in the claim's unit, fully written out (for example 94900000, not "9.49 crore"; a percentage as 82.09), or null>,
 "as_of_date": <date the official figure refers to, YYYY-MM-DD, or null>,
 "confidence": <number from 0 to 1: how likely your verdict is correct>,
 "reason": <one sentence>}}
SUPPORTED means an official source states a figure that agrees with the claim. CONTRADICTED means an official source states a different figure for the same metric, place and period. If you are not certain an official source states this exact figure, answer CANNOT_VERIFY with null source and figure. Do not guess a URL."""
STOP_WORDS = re.compile(r"billing|payment|per ?day|perday|exhausted|limit: 0", re.I)


class StopRun(Exception):
    pass


def read_key():
    with open(os.path.join(ROOT, ".env"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("GEMINI_API_KEY missing: add it to .env")


def build_prompt(claim, lang):
    text = claim["claim_text_hi"] if lang == "hi" else claim["english_gloss"]
    return PROMPT.format(scheme=SCHEME_NAMES[claim["scheme"]], claim=text, date=claim["pub_date"])


def cache_path(model, cid, lang, phash):
    return os.path.join(RAW, model, f"{cid}_{lang}_{phash}.json")


def is_per_minute_429(body):
    """True only when every quota violation named in a 429 is a per-minute limit."""
    try:
        details = json.loads(body)["error"].get("details", [])
    except (ValueError, KeyError, TypeError):
        return False
    ids = [v.get("quotaId", "") for d in details for v in d.get("violations", [])]
    return bool(ids) and all("PerMinute" in i for i in ids)


def call(model, prompt, key):
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }).encode()
    req = urllib.request.Request(ENDPOINT.format(model), data=body, method="POST", headers={
        "Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def call_with_retry(model, prompt, key, log):
    for attempt in range(6):
        try:
            return call(model, prompt, key)
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")
            if e.code == 429 and is_per_minute_429(text):
                wait = 20 * 2 ** attempt
                log(f"429 per-minute, waiting {wait}s")
                time.sleep(wait)
                continue
            if STOP_WORDS.search(text) or e.code in (400, 401, 403, 429):
                raise StopRun(f"HTTP {e.code}: {text[:600]}")
            if e.code in (500, 502, 503, 504):
                wait = 15 * 2 ** attempt
                log(f"HTTP {e.code}, waiting {wait}s")
                time.sleep(wait)
                continue
            raise StopRun(f"HTTP {e.code}: {text[:600]}")
        except (urllib.error.URLError, TimeoutError) as e:
            wait = 15 * 2 ** attempt
            log(f"network error {e}, waiting {wait}s")
            time.sleep(wait)
    raise StopRun("gave up after 6 attempts")


def run_model(model, claims, key, stop, counts, lock):
    os.makedirs(os.path.join(RAW, model), exist_ok=True)
    pause = MODELS[model]

    def log(msg):
        with lock:
            print(f"[{model}] {msg}", flush=True)

    for c in claims:
        for lang in LANGS:
            if stop.is_set():
                return
            prompt = build_prompt(c, lang)
            phash = hashlib.sha256((model + "\n" + prompt).encode("utf-8")).hexdigest()[:12]
            path = cache_path(model, c["id"], lang, phash)
            if os.path.exists(path):
                continue
            started = time.time()
            try:
                status, resp = call_with_retry(model, prompt, key, log)
            except StopRun as e:
                log(f"STOP: {e}")
                stop.set()
                return
            record = {"model": model, "claim_id": c["id"], "lang": lang, "prompt_hash": phash,
                      "called_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "http_status": status, "prompt": prompt, "response": resp}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=1)
            with lock:
                counts[model] += 1
            log(f"{c['id']} {lang} done ({counts[model]} calls)")
            time.sleep(max(0.0, pause - (time.time() - started)))


def parse_answer(resp):
    """Return (parsed dict or None, raw text)."""
    try:
        parts = resp["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    except (KeyError, IndexError, TypeError):
        return None, ""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None, text
    try:
        obj = json.loads(m.group(0))
    except ValueError:
        return None, text
    if isinstance(obj, list):
        obj = obj[0] if obj and isinstance(obj[0], dict) else None
    return (obj if isinstance(obj, dict) else None), text


def write_results(claims):
    rows = []
    for model in MODELS:
        for c in claims:
            for lang in LANGS:
                prompt = build_prompt(c, lang)
                phash = hashlib.sha256((model + "\n" + prompt).encode("utf-8")).hexdigest()[:12]
                path = cache_path(model, c["id"], lang, phash)
                if not os.path.exists(path):
                    continue
                with open(path, encoding="utf-8") as f:
                    rec = json.load(f)
                ans, text = parse_answer(rec["response"])
                ans = ans or {}
                rows.append({
                    "model": model, "model_version": rec["response"].get("modelVersion"),
                    "claim_id": c["id"], "lang": lang, "prompt_hash": phash,
                    "called_at": rec["called_at"], "parsed": bool(ans),
                    "verdict": str(ans.get("verdict") or "").upper().strip() or None,
                    "source_title": ans.get("source_title"), "source_url": ans.get("source_url"),
                    "official_figure": ans.get("official_figure"), "as_of_date": ans.get("as_of_date"),
                    "confidence": ans.get("confidence"), "reason": ans.get("reason"),
                    "raw_text": None if ans else text,
                })
    with open(RESULTS, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only the first N claims (dry run)")
    ap.add_argument("--parse-only", action="store_true", help="rebuild the results file from the cache")
    args = ap.parse_args()
    with open(os.path.join(ROOT, "data", "claims.jsonl"), encoding="utf-8") as f:
        claims = [json.loads(x) for x in f if x.strip()]
    if args.limit:
        claims = claims[:args.limit]
    if not args.parse_only:
        key = read_key()
        stop, lock = threading.Event(), threading.Lock()
        counts = {m: 0 for m in MODELS}
        threads = [threading.Thread(target=run_model, args=(m, claims, key, stop, counts, lock)) for m in MODELS]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        print(f"new calls this run: {counts}; stopped early: {stop.is_set()}")
    print(f"results rows: {write_results(claims)} -> data/verifier_results.jsonl")
    if not args.parse_only and stop.is_set():
        sys.exit(2)


if __name__ == "__main__":
    main()

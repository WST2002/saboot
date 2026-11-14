"""Apply data/labelling-rules.md section 2 to every claim.

Inputs: data/claims.jsonl, data/binding_decisions.jsonl (per-claim decision:
bound / ambiguous / unbindable, chosen evidence and reason), data/binding_evidence.jsonl.
Output: data/bindings.jsonl. For "bound" decisions the label is computed here
(bound+match / bound+mismatch) from the numbers; nothing is typed by hand.
Usage: python -I scripts/label.py"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def strict_match(c, o, p, hedge, percent):
    if hedge == "over":
        return o >= c - 1e-9
    if hedge == "about":
        return abs(o - c) / o <= 0.05
    return abs(round(o / p) * p - c) <= p * 1e-6


def lenient_match(c, o, hedge, percent):
    if percent:
        return o >= c - 1.0 if hedge == "over" else abs(o - c) <= 1.0
    if hedge == "over":
        return o >= 0.95 * c
    return abs(o - c) / o <= 0.05


def main():
    claims = {c["id"]: c for c in load("claims.jsonl")}
    ev = {e["evidence_id"]: e for e in load("binding_evidence.jsonl")}
    decisions = {d["id"]: d for d in load("binding_decisions.jsonl")}
    missing = sorted(set(claims) - set(decisions))
    if missing:
        raise SystemExit(f"No binding decision for: {', '.join(missing)}")
    out = []
    for cid in sorted(claims):
        c, d = claims[cid], decisions[cid]
        rec = {"id": cid, "decision": d["decision"], "reason": d["reason"]}
        if d.get("evidence_id"):
            e = ev[d["evidence_id"]]
            o = float(e["values"][d["key"]])
            percent = c["unit"] == "percent"
            s = strict_match(c["number"], o, c["precision"], c["hedge"], percent)
            le = lenient_match(c["number"], o, c["hedge"], percent)
            rec.update({
                "bound_official_url": e["url"], "official_figure": o, "official_metric_key": d["key"],
                "as_of_date": e["evidence_date"], "evidence_id": e["evidence_id"], "source_type": e["source_type"],
                "evidence_access": e["access"], "evidence_quote": e["quote"], "quote_type": e["quote_type"],
                "strict_match": s, "lenient_match": le,
                "relative_gap": round((c["number"] - o) / o, 6),
            })
            default_conf = 3 if e["access"] == "fetched" else 2
        else:
            rec.update({"bound_official_url": None, "official_figure": None, "as_of_date": None,
                        "strict_match": None, "lenient_match": None})
            default_conf = 2
        if d["decision"] == "bound":
            rec["label"] = "bound+match" if rec["strict_match"] else "bound+mismatch"
        elif d["decision"] == "ambiguous":
            rec["label"] = "bound-ambiguous"
            rec["ambiguity_type"] = d["ambiguity"]
            # Match fields for ambiguous claims are informational only (what the
            # rule would say if the official figure were accepted as the same metric).
        else:
            rec["label"] = "unbindable"
        rec["confidence"] = d.get("confidence", default_conf)
        rec["labelled_by"] = "AI agent (Claude) for the author; not yet human-reviewed"
        out.append(rec)
    with open(os.path.join(ROOT, "data", "bindings.jsonl"), "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"labelled {len(out)} claims")


if __name__ == "__main__":
    main()

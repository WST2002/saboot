"""Print in-window candidate sentences with magnitude words, indexed by line
number in data/candidates.jsonl. Usage: python -I scripts/show_candidates.py [START_ARTICLE] [END_ARTICLE]"""
import json, re, sys
sys.stdout.reconfigure(encoding="utf-8")
lo, hi = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (1, 10**6)
MAG = re.compile(r"[0-9०-९][0-9०-९,.]*\s*(लाख|करोड़|प्रतिशत|फीसदी|%|हजार|हज़ार)")
cur, a = None, 0
for i, line in enumerate(open("data/candidates.jsonl", encoding="utf-8"), 1):
    c = json.loads(line)
    d = c["pub_date"][:10]
    if not ("2026-08-01" <= d <= "2026-11-13"):
        continue
    if c["url"] != cur:
        cur, a = c["url"], a + 1
        if lo <= a <= hi:
            print(f"\n## A{a} {d} {cur[8:100]}")
    if lo <= a <= hi and MAG.search(c["sentence"]):
        print(f"[{i}]", ",".join(c["schemes"]) or "_", c["sentence"][:260])

# Saboot: labelling rules (fixed before labelling, 2026-11-14)

These rules fill the gaps in `methodology.md` §2-3. They were written before any
binding label was assigned and are applied by `scripts/label.py`, which computes
the match decision from the numbers. The human-style judgement (which official
figure is the "same metric, same geography, same period") is recorded per claim
in `data/bindings.jsonl` as `evidence_metric_note` and `reason`.

## 1. Number normalisation

- 1 हजार = 1e3, 1 लाख = 1e5, 1 करोड़ = 1e7; "लाख करोड़" = 1e12; Devanagari digits converted.
- Compound Indian forms are summed: "1 करोड़ 7 लाख 87 हजार 724" = 10,787,724.
- "X हजार Y करोड़" means (X thousand + Y) crore: "18 हजार 690 करोड़" = 18,690 crore.
- Number words ("आठ लाख आठ हजार") are entered by hand (`value` field) and flagged in `data/curation.jsonl`.
- **Precision** p = place value of the last digit the claim states ("9.34 करोड़" → p = 0.01 crore = 1e5; "82.47%" → 0.01 pp; "60 करोड़" → 1 crore).
  Trailing zeros written as digits count as stated ("18,700 करोड़" → p = 1 crore). This is the
  conservative reading; a journalist's rounding to the nearest hundred crore then fails the strict
  rule and passes the lenient one, and both results are reported.

## 2. Match rule (strict and lenient)

Let C = claim value, O = official value.

| Claim hedge | Strict match | Lenient match |
|---|---|---|
| none (exact figure) | O rounded to precision p equals C | \|O − C\| / O ≤ 5% |
| "से अधिक / से ज्यादा / over" | O ≥ C (methodology §2) | O ≥ 0.95 × C |
| "लगभग / करीब / about / के पास" | \|O − C\| / O ≤ 5% (methodology §2) | same as strict |

Percentages (coverage %): strict as above (rounding at stated decimals; "over" → O ≥ C);
lenient = within ±1.0 percentage point (a relative 5% band would allow ±4 pp at 80%, too loose).

The **label** uses the strict rule. `lenient_match` is stored alongside so results can be reported under both.

## 3. When is an official figure "the same metric, geography, period"?

- **Event figures** (one instalment, one approval, one month): the official figure must describe the same event (e.g. the 24th PM-KISAN instalment of 30 Oct 2026). Pre-release announcements ("मिलेगी", "will receive") are compared with the official figure for that same release.
- **Cumulative stocks** (cards made, houses completed, tap connections): the evidence date must be within **±31 days** of the claim's time reference (the article date when the claim says "अब तक"). Evidence on or before the article date is preferred (methodology §3). If the only official figure is further away in time, the label is **bound-ambiguous (period gap)** and both dates are recorded.
- **Definition clash** → bound-ambiguous: e.g. "people treated" vs "hospital admissions"; "cards" vs "people with cards"; PMAY-G only vs "PM Awas" including state/PM-JANMAN houses; registered vs paid farmers; PMAY-U vs PMAY-U 2.0.
- **Several conflicting official figures** for the same metric and period → bound-ambiguous, all recorded.
- A claim whose number is internally impossible (e.g. "447 लाख करोड़") is compared like any other; the reason notes the likely unit slip.

## 4. Search budget and source order

Sources tried, in this order (methodology §2): PIB (Hindi/English) → scheme dashboard
(PMAY-G report pages, pmuy.gov.in, pmay-urban.gov.in, pmkisan.gov.in; Wayback where a dated
snapshot exists) → Parliament answers (sansad.in, via PIB/news pointers) → data.gov.in (not
used: needs a registered API key).

**unbindable** = no official figure for the same metric and geography found with that order.
The reason states what was checked. Claims whose geography is a state and whose metric is
published only in state-government releases (not in the listed central sources) are
unbindable under this protocol, even if a state press note exists.

## 5. Access limits on 2026-11-14 (affects evidence quality)

- **pib.gov.in returned HTTP 403** to the study's fetcher and to the WebFetch tool on
  2026-11-14 (it was reachable earlier the same morning, see data-sources.md). The study did
  not try to get around the block. PIB figures were therefore taken from **search-engine
  extracts of the PIB page** (WebSearch restricted to pib.gov.in), which quote the page text.
  These bindings carry `evidence_access: "search_extract"` and `confidence: 2` at most; the
  author must open each PIB URL in a browser and confirm the quoted figure before the report.
- Pages fetched directly are stored under `data/raw/` and carry `evidence_access: "fetched"`.
- jagran.com and navbharattimes.indiatimes.com (the methodology's 2nd and 3rd outlets) refuse
  Anthropic's agent user agent, as do bbc.com (robots.txt Disallow for ClaudeBot), jansatta.com
  and hindi.oneindia.com. They were replaced by Patrika, Prabhat Khabar and Aaj Tak (robots.txt
  allows all agents, or explicitly allows ClaudeBot for Patrika and Amar Ujala). One Jagran
  topic page fetched at 10:30 before this was noticed was deleted from `data/raw/`.
- zeenews.india.com returned 403/404/410 to the fetcher; its articles were dropped.

## 6. Scope decisions (deviations from methodology.md, stated up front)

- **Geography:** only India- and state-level claims are kept (the methodology's `geography`
  field is "India/state"). District figures were seen in many articles but excluded.
- **Article discovery:** by web search (methodology allows `site:` search) plus tag pages, not
  strictly newest-first per scheme; queries are logged in the agent transcript, articles in
  `data/articles_log.jsonl` (every article fetched, including ones with no usable claim).
- **Rule claims** (₹6,000 a year, ₹1.20 lakh per house, ₹5 lakh cover) are not counted.
- **One sentence, several numbers:** each number tied to a different metric is a separate claim
  (e.g. farmers and rupees in the same sentence); `claim_text_hi` is the verbatim clause.
- **Dedup:** same scheme + metric + geography + normalised number within 7 days → keep the
  earliest (ties: first extracted); duplicates are listed inside the kept claim.
- **Outlet cap (40):** Prabhat Khabar has 42 claims; see summary.md. The cap was not enforced
  because dropping claims would have pushed the total below 100 (methodology minimum 80).

## 7. Who produced the labels (AI assistance statement)

Labels were produced **by an AI agent (Claude, Anthropic; run inside Claude Code on the
author's laptop) on behalf of the author, Wageesha Tripathi**, on 2026-11-14:

1. Article discovery: the agent ran web searches and fetched articles (`scripts/fetch.py`,
   polite 3 s delay, cached raw HTML).
2. Sentence extraction: `scripts/extract.py` pulled every sentence with a number; the agent read
   them and chose the claims, wrote the verbatim clause, the English gloss, scheme, metric,
   geography, time reference, speaker and hedge (`data/curation.jsonl`).
   `scripts/build_claims.py` verifies every clause appears verbatim in the stored raw HTML,
   normalises the number, and deduplicates.
3. Binding: the agent searched the official sources in §4 and recorded the official figure,
   date, URL and a verbatim evidence quote (`data/binding_evidence.jsonl`).
4. Labelling: `scripts/label.py` applies §2 mechanically; the metric/period alignment decision
   (§3) is the agent's and is written out per claim.

**The author has not yet reviewed these labels.** Before the gold set is frozen (methodology
§3: labels fixed before any LLM verifier run), the author must re-check every binding, in
particular all `search_extract` evidence, and the 20% blind second pass must be done by a
human. Because the first-pass labeller is itself an LLM, the report must say so; using these
labels unreviewed as "human gold" would be wrong.

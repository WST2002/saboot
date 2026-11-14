# Saboot: methodology

Working title: **Saboot: How much of Hindi news about government schemes can be bound to official numbers, and do LLM verifiers know when they can't?**

Tracks: Track 2 (Trust Infrastructure: "What share of a domain's content can be automatically linked to checkable evidence?") with the Track 4 "numerical-claims cross-check" angle.

## Research questions

- **RQ1 Coverage:** What fraction of numerical claims about central schemes in Hindi news can be bound to a dated official statistic?
- **RQ2 Agreement:** Of the bound claims, how often does the number match?
- **RQ3 Verifier behaviour:** Do free LLM verifiers bind claims to the right official figure, and do they say "cannot verify" when no evidence exists, instead of inventing a source?
- **RQ4 Language (if time):** Does the same verifier behave differently on the Hindi vs English wording of the same claim?

## 1. Claim selection protocol

**Target:** 100 claims (minimum 80 to publish; stop at 120).

**Schemes (6):** PM-KISAN, PMAY (Gramin + Urban counted as one scheme, sub-tagged), PM Ujjwala, Jal Jeevan Mission, Ayushman Bharat PM-JAY, MGNREGA. Quota ~17 per scheme; if a scheme yields fewer, fill from the others and report the real split.

**Date window:** articles published **1 Aug 2026 to 13 Nov 2026**. Recent enough that PIB releases, dashboards and Wayback snapshots for the same period exist.

**Sources:** Amar Ujala, Dainik Jagran, Navbharat Times (see data-sources.md). Cap 40 claims per outlet so one outlet does not dominate.

**Finding articles:** for each scheme use the outlet's tag/topic page or news sitemap, plus a search `site:<outlet> "<scheme name in Hindi>"`. Take articles in reverse date order (newest first) until the quota is met. Log every article visited, including ones with no usable claim (this gives the denominator for "articles with any numerical claim").

**What counts as a claim (inclusion):**
- One sentence (or clause) with a number tied to a central scheme metric: beneficiaries, households, houses, connections, amount disbursed, instalments, person-days, coverage %, budget.
- The number may be in Devanagari or Arabic digits, with लाख / करोड़ / प्रतिशत / हजार.

**Exclusions:** dates and instalment ordinals alone ("24वीं किस्त") unless paired with an amount; per-person entitlement amounts that are scheme rules ("₹6000 प्रति वर्ष") — tag these separately as *rule claims*, do not count them in the 100; state-only schemes; forecasts/targets stated as future ("2027 तक") unless the official target is published; quotes from opposition parties are allowed but tagged by speaker.

**Dedup:** if two outlets carry the same number for the same metric in the same week, keep one (the earliest) and note the duplicate.

**Record per claim (claims.csv):** `id, outlet, url, pub_date, headline, claim_text_hi, number_raw, number_normalised, unit, scheme, metric, geography (India/state), time_reference (as stated), speaker (govt/official/opposition/journalist), english_pair_url (if any)`.

**Number normalisation:** 1 लाख = 1e5, 1 करोड़ = 1e7; convert Devanagari digits (०-९); keep the claim's precision (number of significant figures) for the match rule.

## 2. Labels

| Label | Definition |
|---|---|
| **bound + match** | An official dated source reports the same metric, same geography, same period, and the number agrees under the match rule. |
| **bound + mismatch** | Same metric/geography/period found, number disagrees beyond tolerance. |
| **bound-ambiguous** | Official numbers exist but cannot be aligned without a judgement call: different metric definition (sanctioned vs completed vs grounded houses; registered vs paid farmers), cumulative vs annual, period unclear, several conflicting official figures. Record which. |
| **unbindable** | No official figure found within the search budget (15 min per claim, sources in data-sources.md order: PIB same language → PIB other language → scheme dashboard / Wayback → Parliament answers → data.gov.in). |

**Match rule:** the official value, rounded to the claim's stated precision, equals the claim (e.g. official 105,685,306 = 10.57 करोड़; a claim "10.5 करोड़" is a strict mismatch because 10.57 rounds to 10.6, but a lenient match because the gap is under 5%; a claim "10.6 करोड़" is a strict match). If the claim is hedged ("लगभग", "करीब", "से अधिक"), apply: "से अधिक/over" → official ≥ claim; "लगभग/about" → within ±5%. Report results under both strict (rounding only) and lenient (±5%) rules.

**Evidence record per bound claim:** `evidence_url, evidence_date, evidence_value, evidence_quote (verbatim, short), source_type (PIB/dashboard/Parliament/data.gov), language_of_evidence`.

## 3. Human labelling rubric

1. Read the claim; fill scheme, metric, geography, period. If period is not stated, assume "as on article date" and mark `period_assumed=1`.
2. Search sources in the fixed order above; stop at the first source that states the same metric for the same geography and the nearest date **on or before** the article date.
3. Apply the match rule; pick a label.
4. Write one line of rationale, especially for *ambiguous* (which definition clash).
5. Confidence 1-3.

**Reliability:** primary annotator labels all claims. A blind second pass on a random 20% subset (by a second person if available, else the same annotator after >12 h with the first labels hidden). Report Cohen's kappa on the 4-way label. Labels are fixed **before** any LLM is run (prevents leakage into the gold set).

## 4. LLM-verifier protocol

**Models (free):** Gemini API free tier through Google AI Studio (a Flash and a Flash-Lite model; exact model names and per-day limits to be read from https://aistudio.google.com/rate-limit on the day and written into the report). Optional second family if free and available: a local open-weights model through Ollama. Temperature 0. Record model id + date of every call.

Rate-limit budget: 100 claims × 3 conditions × 2 languages (subset) × 2 models ≈ 800-1,000 calls. Spread over the day; cache every response to disk (jsonl) so nothing runs twice.

**Conditions:**

- **C1 Closed-book (no evidence):** the model gets only the claim. Measures whether it invents a source.
- **C2 Gold evidence:** the claim plus the official evidence snippet the human found (for bound claims) or the best near-miss snippet (for unbindable). Measures binding + matching ability.
- **C3 Distractor evidence:** the claim plus an official snippet for the same scheme but wrong metric or wrong date. Measures whether it abstains or forces a match.

**Prompt (C1; C2/C3 add an `EVIDENCE:` block and "use only the evidence"):**

```
You check numerical claims about Indian government schemes against official statistics.
CLAIM: <claim text>
ARTICLE DATE: <date>
Answer in JSON only:
{"verdict": "MATCH" | "MISMATCH" | "CANNOT_VERIFY",
 "official_value": <number or null>,
 "source_url": <official URL you rely on, or null>,
 "source_date": <date or null>,
 "reason": <one sentence>}
If you are not certain an official source states this exact figure, answer CANNOT_VERIFY with nulls. Do not guess a URL.
```

Same prompt in Hindi for the language comparison (translated once, checked by the native-speaker author, fixed for all runs).

**Hindi vs English (RQ4):** use 30 claims. Best pairing: the same release in PIB Hindi and PIB English (identical facts, different language), plus any Navbharat Times / Times of India pairs found while collecting. Each pair gets the same condition and model; compare with McNemar's test on correct/incorrect.

**Automatic checks on model output:**
- `source_url` resolves? (HTTP GET, record status) Contains the claimed `official_value` (after normalisation)?
- Hallucinated source = a non-null URL that does not resolve, or resolves but does not contain the value, or is not an official domain (gov.in / nic.in / sansad.in / pib.gov.in) while presented as official.

## 5. Metrics

- **Coverage (RQ1)** = (bound+match + bound+mismatch + bound-ambiguous) / all claims; also strict coverage = (match + mismatch) / all. Break down by scheme, outlet, speaker.
- **Match rate (RQ2)** = match / (match + mismatch), strict and lenient rules.
- **Binding precision** = of model outputs with a non-null official value, fraction whose value + source agree with the human evidence.
- **Binding recall** = of human-bound claims, fraction the model bound correctly.
- **Verdict accuracy** vs human label (CANNOT_VERIFY counts as correct for unbindable).
- **Abstention rate** on unbindable claims (want high) and **false abstention rate** on bindable claims with gold evidence (want low).
- **Hallucinated-source rate** = hallucinated sources / outputs with a non-null source (C1 is the headline number).
- All proportions with **Wilson 95% intervals**; n is small, so report counts, not just percentages.

## 6. Timeline (IST; hard deadline 16 Nov 17:29 IST, own target 16 Nov 12:00)

| When | Work |
|---|---|
| Sat 14 Nov 10:30-14:00 | Article collection + claim extraction into claims.csv (target 100) |
| Sat 14 Nov 14:00-20:00 | Human binding + labels (about 3 min per easy claim, 15 min cap) |
| Sat 14 Nov 20:00-23:00 | AI Studio key, verifier script, URL checker, dry run on 10 claims |
| Sun 15 Nov 07:00-08:00 | 20% second-pass labels, kappa |
| Sun 15 Nov 08:00-15:00 | Full LLM runs (C1-C3, both models, Hindi/English subset), cached |
| Sun 15 Nov 15:00-20:00 | Analysis, CIs, 2 figures (coverage stacked bar by scheme; verifier confusion/abstention chart) |
| Sun 15 Nov 20:00 - Mon 16 Nov 10:00 | Write report in the template (Google Doc), appendix, LLM usage statement |
| Mon 16 Nov 10:00-12:00 | Re-check every number and reference against data files; export PDF; submit |
| 12:00-17:29 | Buffer only |

Cut order if late: drop RQ4 first, then C3, then the second model.

## 7. Submission format (official template)

- Template: Google Doc, https://docs.google.com/document/d/17b3JWki-ZkaqdmqGI5d0gof-HwlGuWU9Mc1_klNZXKs/copy (local copies: apart-submission-template.docx and .txt in this folder).
- Sections: Title, authors + affiliation ("With Apart Research"), Abstract (150-250 words), 1 Introduction (with contribution list), 2 Related Work, 3 Methods, 4 Results (at least one numbered figure), 5 Discussion and Limitations (+ Future Work), 6 Conclusion, Code and Data, Author Contributions (optional), References, Appendix, **LLM Usage Statement**.
- Template recommends ~4 pages (Intro+RW 1p, Methods+Results 2.5p, Discussion 0.5p); sprint hard cap 8 pages excluding references/appendices. Export as PDF. Footnote: "Research conducted at the AI x Epistemics Research Sprint, November 2026".
- Required appendix: **"Limitations and Dual-Use / Ethical Considerations"** (below).
- Disqualification risk: any made-up result or reference. Every number in the PDF must trace to claims.csv / results files.

## 8. Limitations (draft)

- Small sample (~100), three outlets, one language pair, 3.5-month window; not representative of all Hindi media.
- Single primary annotator; kappa only on a subset.
- "Unbindable" depends on the 15-minute search budget and on what the government publishes; it measures *publicly checkable* evidence, not truth.
- Dashboards are live; past values recovered from Wayback/PIB may be incomplete. A mismatch can be a date lag, not an error.
- Official statistics are themselves claims; binding a news number to them checks consistency, not ground truth.
- Free-tier models only; results may not transfer to frontier paid models or to later versions.
- Hindi translation of the prompt by one author.

## 9. Dual-use / ethical considerations (draft)

- **Selective use:** a mismatch list could be cherry-picked to attack outlets or the government. Report aggregate rates and every claim with its evidence, including the many matches; describe mismatches as measurement outcomes, not accusations of lying.
- **Gaming:** publishers could learn to phrase claims vaguely ("करोड़ों") to stay unbindable. Report vague-claim rate as its own number so this is visible.
- **Over-trust in verifiers:** showing LLMs invent official URLs is the point; the tool must not be presented as an automatic truth checker.
- **Personal data:** only aggregate scheme statistics are collected. Scheme portals expose beneficiary-level lists; these are never opened, scraped or stored. No personal data handled.
- **Server load and copyright:** polite crawling (one request every few seconds, robots.txt respected, Live Hindustan and Bhaskar excluded); store only URL, date, headline and the claim sentence, not full articles.
- **Political neutrality:** schemes chosen by coverage volume, not by party; speakers tagged so results can be split by who made the claim.

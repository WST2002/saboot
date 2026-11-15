# Saboot: How Much of Hindi News About Government Schemes Can Be Bound to Official Numbers, and Does an LLM Verifier Know When It Can't?

AUTHOR: Wageesha Tripathi | Independent, Varanasi, India | tripathiwageesha2002@gmail.com

ABSTRACT: A Hindi newspaper reported that "about 10 crore" farmers received the 24th PM-KISAN instalment. The official figure was 9.34 crore, so the claim was 7.1% too high. We collected 102 such numerical claims about six central schemes from four Hindi outlets. We asked how many can be tied to a dated official statistic, and whether an LLM verifier can tell when they cannot. Only 45.1% of claims (46/102) could be bound to an official statistic, and 24.5% cleanly. National claims were bound far more often than state claims (69.2% against 20.0%). Of the 25 cleanly bound claims, 88.0% matched. We then tested a free LLM verifier, gemini-3.5-flash-lite, on every claim in Hindi and English. Without evidence, it answered "cannot verify" in 92.2% of its 204 responses. Its abstention rate was almost the same whether official evidence existed (92.0%) or not (93.8%). Abstention was not the only problem: when it committed, it was usually wrong, and none of its cited sources showed its figure; one cited PIB release is about a Holi special train. Given the official excerpt, false abstention on cleanly bound claims fell from 92.0% to 0.0%, and 97.7% of answers on matching claims were MATCH. But the verifier never labelled an ambiguous claim AMBIGUOUS (0 of 42 answers), and it called 13.6% of near-miss answers a mismatch. Its overall agreement (68.8%) stayed below a simple excerpt-type baseline (76.2%). Verifiers in this domain should be judged on whether their answers follow the evidence, not on how often they abstain.

## 1. Introduction

On 30 October 2026, Patrika reported that "about 10 crore" farmers had received the 24th PM-KISAN instalment. The Press Information Bureau (PIB) note for that day says 9.34 crore (also written "more than 9.34 crore"; "about 10 crore" would pass only if the true count were at least 9.524 crore). That is 7.1% above the official figure, and our rules allow only ±5% for "about" (Table C.3). Hindi newspapers report government schemes in numbers like this every day, and for many readers these articles are how they learn whether a scheme works. Most such numbers have an official counterpart: dated PIB releases in Hindi and English, scheme dashboards, and Parliament answers. Few people check. The sources are scattered, often in English, and dashboards overwrite last month's figure with today's.

AI research agents now get the same question: is this number right? When no official figure exists, the honest answer is "I cannot verify this". The failure we care about is false verification: an agent cites an official-looking source that does not support the claimed number, so an unchecked claim looks checked.

We call linking a claim to a specific, dated official statistic **binding**. Before judging a verifier, one needs to know how much of the domain can be bound at all, and what the right answer is for each claim. We measure that first. Then we test one LLM verifier twice: from memory (**closed-book**) and with the official excerpt in the prompt (**evidence-given**). Our research questions are:

- **RQ1 Coverage.** What share of numerical claims about central schemes in Hindi news can be bound to a dated official statistic?
- **RQ2 Agreement.** When a claim binds cleanly, how often does the number match?
- **RQ3 Closed-book.** Without evidence, does the verifier abstain when no official figure exists, commit when one does, and cite sources that show the figure?
- **RQ4 Evidence-given.** With the official excerpt in hand, does it reach the right label, including "ambiguous" and "cannot verify"?
- **RQ5 Language.** Does the Hindi or the English wording of a claim change the answer?

**Our main contributions are:**

1. A dataset of 102 real numerical claims from four Hindi outlets, each bound to a dated official source with a verbatim quote, or marked unbindable with the reason.
2. A binding study: how many claims bind cleanly, ambiguously or not at all, by scheme, outlet, geography and speaker, and how often bound claims agree.
3. Two evaluations of a free LLM verifier on the same claims in Hindi and English: closed-book, with a check of every cited URL, and evidence-given, with fixed official excerpts, including near-miss excerpts that look relevant but lack the claim's figure.

## 2. Related Work

**Numerical fact-checking.** Vlachos and Riedel (2015) checked simple statistical claims against a knowledge base. QuanTemp (Venktesh et al., 2024) collected 15,514 real numerical and temporal claims in English, with web-snippet evidence. The CLEF-2026 CheckThat! lab (Struß et al., 2026) covers numerical claims in English, Spanish and Arabic, not Hindi. NumPert (Aarnes and Setty, 2025) perturbs numbers to probe LLM veracity predictions.

**Claims over tables.** The closest work, Devasier et al. (2026), generates synthetic claims from OECD tables in four languages including Hindi; the evidence is not Indian government data. ClaimDB (Theologitis et al., 2026) verifies claims over large real databases and finds that models struggle to abstain; it is English and not tied to news.

**Indian languages and abstention.** IndicClaimBuster (Pal et al., 2025) offers about 9,000 claims from Indian news in English, Hindi, Bengali and code-mixed text; the IndicClaimVer shared task at FIRE 2026, co-organised by its first author, benchmarks claim verification in Indian languages. HiFACTMix (Thakur et al., 2025) has 1,500 code-mixed Hinglish political claims, and X-FACT (Gupta and Srikumar, 2021) is a multilingual benchmark. None focus on numbers or use official statistics as evidence. REASONS (Tilwani et al., 2024) asks whether LLMs abstain or hallucinate when attributing scientific citations; we ask the same of official statistics. **Gap:** we found no work that measures, on real Hindi news, how much numerical content can be bound to government statistics, how often it agrees, and whether a verifier's answers follow that boundary, with and without the evidence.

## 3. Methods

### 3.1 Claim sampling

We studied six central schemes chosen by volume of news coverage, not by political association: PM-KISAN, PMAY (Gramin and Urban together), PM Ujjwala (PMUY), Jal Jeevan Mission (JJM), Ayushman Bharat PM-JAY and MGNREGA. Two of the three planned outlets (Dainik Jagran, Navbharat Times) and several others refused the study's crawler; we did not circumvent refusals, kept Amar Ujala and added Patrika, Prabhat Khabar and Aaj Tak, whose robots.txt files allow it. Articles from 1 August to 13 November 2026 were found by site-restricted search and tag pages, and every fetch was logged.

A claim is one clause with a number tied to a central scheme metric (beneficiaries, houses, connections, amount disbursed, person-days, coverage or budget), at India or state level. We excluded bare dates, instalment ordinals, state-only schemes, future targets and fixed entitlements, and dropped duplicates (same number, scheme, metric and geography within 7 days). Each claim records outlet, URL, date, the verbatim Hindi clause, an English gloss, the normalised number (1 लाख = 100,000, 1 करोड़ = 10,000,000, stated precision kept), scheme, metric, geography, period, hedge and speaker. A script confirmed every clause verbatim in the stored article.

### 3.2 Labels and binding rules

Each claim received one of four labels. **Bound + match**: an official dated source reports the same metric, geography and period, and the number agrees under the match rule. **Bound + mismatch**: same metric, geography and period, but the number disagrees beyond the rule. **Bound-ambiguous**: official numbers exist but cannot be aligned without a judgement call (a different definition, a period gap, or conflicting official figures). **Unbindable**: no official figure for the same metric and geography was found in the listed sources.

Sources were searched in a fixed order: PIB in the claim's language, PIB in the other language, the scheme dashboard or its Wayback Machine snapshot, and Parliament answers, preferring the nearest date on or before the article date. For a cumulative stock (houses completed, tap connections) the official date had to be within 31 days of the claim's time reference; otherwise the claim was bound-ambiguous (period gap).

**Match rule:** the official value, rounded to the claim's stated precision, must equal the claim; trailing zeros count as stated, so "18,700 crore" is read as exact to the crore. "से अधिक" (over) requires official ≥ claim, and "लगभग" or "करीब" (about) allows ±5% of the official value. The lenient rule also accepts a gap of up to 5%. The rules were written down before any label was assigned.

### 3.3 Validation and provenance

This is an exploratory, single-annotator dataset. Articles were found, claims chosen, sources searched and each figure, date, URL and verbatim quote recorded with a rationale, under the written rules (data/labelling-rules.md). Every official page behind a binding was then opened in a browser. For all 46 bound or ambiguous claims, the figure and scope were checked against the record; for 36 of them, the as-of date was checked too. Ten bindings were corrected, including one label and five where a release date had been recorded instead of the figure's date. A script found all 73 evidence quotes, from 19 official pages, verbatim in the saved page text. This confirms that the evidence is on the page, not every alignment judgement. All labels were fixed before any verifier call.

### 3.4 Verifier experiments

**Model.** All results are for **gemini-3.5-flash-lite** on the free Gemini API tier, at temperature 0, one run per condition; it was the only planned model we could run in full, so there is no model comparison (gemini-2.5 models returned HTTP 404 for new users on 14 November 2026; gemini-3.8-flash returned repeated HTTP 503 errors and allows 20 requests a day).

**Closed-book (C1).** The model saw the scheme name, the claim and the article date, nothing else, and returned a verdict (SUPPORTED, CONTRADICTED or CANNOT_VERIFY), the source title and URL, the official figure and its date, a confidence from 0 to 1 and a reason. It was told to answer CANNOT_VERIFY unless certain and not to guess a URL (Appendix B.1). Each claim was sent twice, as the Hindi clause and as its English gloss: 204 answers on 14 November 2026.

**Evidence-given (C2).** The model saw the same claim plus an official excerpt, was told to use only that evidence, and chose one of four labels that mirror the gold labels: MATCH, MISMATCH, AMBIGUOUS or CANNOT_VERIFY (Appendix B.2). It also returned the figure, date and exact phrase it relied on. Excerpts were cut from the official page texts saved in the browser check by two fixed rules (scripts/build_evidence_excerpts.py):

- *Bound and ambiguous claims (46):* the passage around the verified evidence quotes, 1,200 characters from one page, or a shorter window from each page when the binding used several.
- *Unbindable claims: a near-miss excerpt.* Its purpose is to test whether the verifier recognises evidence that looks relevant but cannot settle the claim, so the right answer is CANNOT_VERIFY. Among the saved pages for the same scheme, we took the 1,200-character window sharing the most content words with the claim (with a bonus for naming its state), skipping any window that contains the claim's number in any written form. C057 shared no word with any page and was not sent, leaving 55 near-misses; 13 of them held some number within 25% of the claim's and were flagged before the run.

All 101 excerpts were frozen before any call: each block was saved with a SHA-256 hash, and the run script refuses any block whose hash has changed. The 202 calls ran on 14 November 2026 (UTC). One design difference: only the C2 prompt names the claim's figure on its own line ("FIGURE TO CHECK").

**Scoring.** In C1 the expected verdict is SUPPORTED for bound + match, CONTRADICTED for bound + mismatch, and CANNOT_VERIFY for ambiguous and unbindable claims, which have no clean official figure. In C2 it is the gold label. A **false abstention** is CANNOT_VERIFY (or, in C2, AMBIGUOUS) on a cleanly bound claim. In C1 every cited URL was requested (3 seconds apart) and non-PIB pages were also opened in a browser. A cited source **fails** if it does not load, does not show the stated figure, or is not an official government domain; for PIB we checked that the release ID exists and that its title names the claim's scheme.

### 3.5 Metrics

Coverage = (match + mismatch + ambiguous) / all claims; strict coverage = (match + mismatch) / all; match rate = match / (match + mismatch). Proportions carry Wilson 95% intervals, which treat claims as independent although several share an article, so they are optimistic. Pooled results count each claim twice (Hindi and English), so pooled intervals are optimistic for the same reason. Hindi and English answers are compared with an exact McNemar test on claims right in one language only. Baselines: always CANNOT_VERIFY, and, in C2, MATCH for every bound or ambiguous claim and CANNOT_VERIFY for every near-miss; this second baseline uses the excerpt type, which a deployed verifier would not know. All numbers come from scripts/report_tables.py, score_verifier.py and score_evidence.py.

## 4. Results

### 4.1 Coverage (RQ1)

**Fewer than half of the claims could be bound, and state claims rarely.** From 79 attempted article fetches (73 succeeded) and after removing 21 duplicate claims, the dataset has 102 claims from 37 articles (2 August to 11 November 2026): 42 from Prabhat Khabar, 26 Aaj Tak, 22 Patrika and 12 Amar Ujala; 52 national and 50 state-level; 70 in the journalist's own words. Coverage was 45.1% (46/102, 95% CI 35.8-54.8%) and strict coverage 24.5% (25/102, CI 17.2-33.7%); 21 claims were bound only ambiguously and 56 were unbindable (Figure 1, Table C.7).

FIGURE: report/figures/fig1_labels_by_scheme_geography.png | 3.9 | **Figure 1.** Binding labels for the 102 claims (strict rule), by scheme (top) and by geography (bottom). Numbers inside bars are claim counts; n is the number of claims per row. Ambiguous means official figures exist but use a different definition or period.

Geography makes the largest difference. National claims had 69.2% coverage (36/52, CI 55.7-80.1%) and state claims had 20.0% (10/50, CI 11.2-33.0%). The intervals do not overlap. The recorded reasons concern what our searched sources publish (search effort was not logged): state-wise PM-KISAN instalment figures were in none of the central sources we searched, the JJM dashboard loads its state rows by JavaScript, and state-government releases were outside the source list. By outlet, coverage ranged from 36.4% to 52.4% with overlapping intervals (Table C.1). The 21 ambiguous claims carry 25 recorded reasons: period gap (13), conflicting official figures (5), definition difference (5) and an imprecise official figure (2).

### 4.2 Agreement (RQ2)

**When a number could be bound cleanly, it usually matched.** The strict match rate was 88.0% (22/25, CI 70.0-95.8%) and the lenient rate 92.0% (23/25, CI 75.0-97.8%). All three strict mismatches concern the 24th PM-KISAN instalment (Table C.3): a unit slip (447 lakh crore against an official 4.47 lakh crore), the stretched "about 10 crore" from Section 1, and a rounding difference (18,700 crore against Rs 18,690 crore, a match under the lenient rule). Twelve of the 21 ambiguous claims would also fail the strict rule against the nearest official figure, but all lie within 2.6% of it; most are cumulative totals compared with a value dated weeks or months away (Table C.4).

### 4.3 Closed-book verifier (RQ3)

**Without evidence, the model abstained on almost everything, whether or not evidence existed.** All 204 answers were valid JSON, and the verifier answered CANNOT_VERIFY in 92.2% of them (188/204; Table 2, Figure 2 top). The model abstained almost equally often when an official figure existed (92.0%, 46/50 on cleanly bound claims) and when none was found (93.8%, 105/112 on unbindable claims). Abstaining is right only for the second group; for the first, a dated official figure exists. Overall accuracy, 71.6% (146/204), was below the 75.5% of a verifier that always answers CANNOT_VERIFY. Half of the abstentions (94/188) said the article date was "in the future"; a plausible, untested explanation is that 2026 lies after the model's training data.

**Abstention was not the only problem. When the model committed, it was usually wrong, and no cited source showed its figure.** The 16 committed answers were right 4 times (25.0%, CI 10.2-49.5%). In 10 the "official figure" was exactly the claim's own number, and 12 gave an as-of date before 2026. All 16 cited a source (12 distinct URLs) and none showed the stated figure: a cited-source failure rate of 100% (16/16, CI 80.6-100%). All 7 PIB links used release IDs that exist, but each opens an unrelated release: a Holi special train, a Sikh New Year greeting, a speech in Warsaw, and four more (Table C.5). The one answer with a correct verdict and a correct figure (C002, Hindi) cited the Holi train. Counting only dead or non-official URLs would flag 4 of 16 and miss every wrong PIB citation. These committed answers carried a mean stated confidence of 0.94 (Table C.6).

TABLE: **Table 2.** gemini-3.5-flash-lite in both conditions, Hindi and English pooled (temperature 0, one run). Closed-book: 204 answers on 102 claims; evidence-given: 202 answers on the 101 claims with an excerpt. Wilson 95% CI in brackets. The expected answer uses the three closed-book verdicts in C1 and the four gold labels in C2. Per-language results: Tables C.8 and C.9.
| Measure | Closed-book | Evidence-given |
|---|---|---|
| Answer equals expected answer | 71.6% (146/204, 65.0-77.3) | 68.8% (139/202, 62.1-74.8) |
| Baseline (Section 3.5) | 75.5% (154/204, 69.2-80.9) | 76.2% (154/202, 69.9-81.6) |
| False abstention, cleanly bound claims | 92.0% (46/50, 81.2-96.8) | 0.0% (0/50, 0.0-7.1) |
| Right answer, bound + match | 4.5% (2/44, 1.3-15.1) | 97.7% (43/44, 88.2-99.6) |
| Right answer, bound + mismatch | 33.3% (2/6, 9.7-70.0) | 66.7% (4/6, 30.0-90.3) |
| Right answer, bound-ambiguous | 88.1% (37/42, 75.0-94.8) | 0.0% (0/42, 0.0-8.4) |
| CANNOT_VERIFY, unbindable claims | 93.8% (105/112, 87.7-96.9) | 83.6% (92/110, 75.6-89.4) |
| MISMATCH on near-miss excerpts | - | 13.6% (15/110, 8.4-21.3) |
| False MATCH on near-miss excerpts | - | 1.8% (2/110, 0.5-6.4) |
| Same answer in Hindi and English | 90.2% (92/102, 82.9-94.6) | 89.1% (90/101, 81.5-93.8) |

### 4.4 Evidence-given verifier (RQ4)

**Given the official excerpt, the model stopped abstaining but did not check comparability.** In the clearest case (C088, Hindi, near-miss excerpt), a claim that "about Rs 500 crore" reached Chhattisgarh farmers was called a mismatch with the national Rs 18,690 crore. The verifier compared the two numbers but did not check that they measured the same thing, in the same place and period. The same failure runs through the ambiguous and near-miss results below (Figure 2, Table 2).

**Clean cases were handled well.** False abstention on cleanly bound claims fell to 0.0%, and 43 of 44 matching answers were MATCH. The two missed mismatch answers are one claim in both languages: the "about 10 crore" farmers (C093), accepted although the 7.1% gap is outside the ±5% that "about" allows.

**AMBIGUOUS was never used where it applied.** On the 42 answers for ambiguous claims the verifier said MATCH 18 times, MISMATCH 18 times and CANNOT_VERIFY 6 times; across all 202 answers it chose AMBIGUOUS once, on an unbindable claim. Every figure in the excerpt was treated as directly comparable. "48.54 crore Ayushman cards" was called a mismatch with "48.51 crore people holding cards", a different count (C044). October claims about national tap coverage were set against 82.09% dated 18 July 2026 and both called mismatches (C063, C068). For C036, where PIB releases give both 81.56% and 81.57% for the same date, the verifier reported the claim's own 81.57% and answered MATCH. In 29 answers the reported figure was the claim's own number. For matching claims that is expected; C036 shows the risk, a pick of whichever official figure agrees with the claim.

**Near-miss excerpts mostly worked, except for false contradictions.** Most near-miss answers were CANNOT_VERIFY, and the two false MATCH answers were both for one flagged claim (C009). The 15 MISMATCH answers, like C088, declared the claim wrong against a figure for another metric or place. A few may be defensible: for C067 the excerpt holds a Rajasthan figure that we had set aside because its table headers were unreadable. For a fact-checker, that is the costly error. An unverifiable claim comes out looking contradicted.

FIGURE: report/figures/fig2_closed_vs_evidence.png | 4.7 | **Figure 2.** Answers of gemini-3.5-flash-lite by gold label, without evidence (top) and with the official excerpt (bottom), Hindi and English pooled, on the 101 claims that received an excerpt (202 answers per panel). Closed-book SUPPORTED and CONTRADICTED are shown as MATCH and MISMATCH. Each row names the expected answer; closed-book had no AMBIGUOUS label, so ambiguous claims expect CANNOT_VERIFY there.

**Overall, the model got better on clean matches and worse on ambiguous evidence.** Four-label agreement was 68.8%, below the 76.2% baseline. On the closed-book scale and the 101 claims with an excerpt, accuracy barely changed: 71.8% (145/202) without evidence and 72.3% (146/202) with it (45 answers right only without evidence, 46 only with it; McNemar p = 1.00). Abstentions on clean claims were replaced by wrong commitments on ambiguous ones.

### 4.5 Hindi versus English (RQ5)

**The wording language changed little, but committed answers were unstable.** The two wordings gave the same answer on 90.2% of claims closed-book and 89.1% with evidence (Table 2). Yet closed-book the model committed on 8 claims in each language, and only 3 were the same claims (C034, C081, C092). Correctness differed between the languages on only 10 claims closed-book (7 right only in Hindi, 3 only in English; exact McNemar p = 0.34) and 9 with evidence (3 and 6; p = 0.51), so neither run can show a language effect.

## 5. Discussion and Limitations

**Coverage reflects what central sources publish.** National totals appear in dated releases; state figures often sit in live JavaScript dashboards.

**A high abstention rate is not the same as knowing when to abstain.** More than half of all claims, and most state claims, have no clean official figure, so a careful verifier should often say "cannot verify". The closed-book verifier said it almost regardless of the claim. By abstention rate alone it looks safe, yet a blanket abstainer scored higher, and its few commitments came with official-looking citations that do not show the figure. This is the false verification the study set out to measure.

**Evidence fixes abstention, not judgement.** With the excerpt, the verifier became a good number comparer. It did not ask whether the official figure measures the same thing, in the same place, at the same time as the claim. For an agent that retrieves official pages, retrieval is the easy half; the hard half is this alignment step.

### Limitations

Appendix A states what the results do and do not establish.

- **One verifier:** one model, one run per condition, temperature 0, free tier; results may not transfer to other models. Half the closed-book abstentions cite a "future" date (an untested cutoff effect).
- **Our excerpts:** chosen by fixed rules (Section 3.4); other windows or pages could change the near-miss results, and only C2 shows the "FIGURE TO CHECK" line, which may itself help. Where a near-miss excerpt gives a related metric or place, AMBIGUOUS is also defensible; MATCH and MISMATCH are wrong either way (the model chose AMBIGUOUS there once).
- **One annotator:** no inter-annotator agreement; the 21 ambiguous claims, which C2 tests most directly, rest on one pass.
- **Small sample:** 102 claims, four outlets, about three months; PMUY (4) and MGNREGA (9) are thin.
- **Language and checks:** AI-written glosses sometimes add context (B.1); checks ran on one day.

### Future Work

More models and runs; a verifier that names metric, place and period first; a second labeller.

## 6. Conclusion

In 102 numerical claims about six central schemes in Hindi news, 45.1% could be bound to a dated official statistic and 24.5% cleanly; cleanly bound claims matched 88.0% of the time. Without evidence, a free LLM verifier said "cannot verify" on 92.2% of answers, almost equally with and without official evidence, and no page it cited showed its figure. With the official excerpt, it labelled 97.7% of answers on matching claims correctly, but never flagged an ambiguous claim and called 13.6% of near-miss answers a mismatch.

Giving the verifier the evidence is only half the job. It must also establish that the official figure measures the same thing, in the same place and period, as the claim. And it should be judged on whether it recognises insufficient or incomparable evidence, not on how often it abstains.

## Code and Data

- **Code repository:** https://github.com/WST2002/saboot (scripts for every step, table and figure).
- **Data/Datasets:** same repository: claims (no full articles), labels, evidence quotes, verifier answers, URL checks, frozen excerpts.
- **Preexisting work:** none; everything was made during the sprint (13 to 15 November 2026).

## References

1. Peter Røysland Aarnes, Vinay Setty. 2025. NumPert: Numerical Perturbations to Probe Language Models for Veracity Prediction. arXiv:2511.09971. https://arxiv.org/abs/2511.09971
2. Jacob Devasier, Akshith Putta, Qing Wang, Alankrit Moses, Chengkai Li. 2026. Frame-Guided Synthetic Claim Generation for Automatic Fact-Checking Using High-Volume Tabular Data. LREC 2026. https://aclanthology.org/2026.lrec-1.136/
3. Ashim Gupta, Vivek Srikumar. 2021. X-FACT: A New Benchmark Dataset for Multilingual Fact Checking. ACL 2021 (short papers). https://aclanthology.org/2021.acl-short.86/
4. IndicClaimVer shared task, FIRE 2026. https://sites.google.com/view/indicclaimver2026
5. Pritam Pal, Shyamal Krishna Jana, Dipankar Das. 2025. IndicClaimBuster: A Multilingual Claim Verification Dataset. Proceedings of IJCNLP-AACL 2025, pp. 2478-2489. https://aclanthology.org/2025.ijcnlp-long.133/
6. Julia Maria Struß, Sebastian Schellhammer, Stefan Dietze, Venktesh V, Vinay Setty, Tanmoy Chakraborty, Preslav Nakov, Avishek Anand, Primakov Chungkham, Salim Hafid, Dhruv Sahnan, Konstantin Todorov. 2026. The CLEF-2026 CheckThat! Lab: Advancing Multilingual Fact-Checking. arXiv:2602.09516. https://arxiv.org/abs/2602.09516
7. Rakesh Thakur, Sneha Sharma, Gauri Chopra. 2025. HiFACTMix: A Code-Mixed Benchmark and Graph-Aware Model for Evidence-Based Political Claim Verification in Hinglish. arXiv:2508.10001. https://arxiv.org/abs/2508.10001
8. Michael Theologitis, Preetam Prabhu Srikar Dammu, Chirag Shah, Dan Suciu. 2026. ClaimDB: A Fact Verification Benchmark over Large Structured Data. ACL 2026. arXiv:2601.14698. https://arxiv.org/abs/2601.14698
9. Deepa Tilwani, Yash Saxena, Seyedali Mohammadi, Ankur Padia, Edward Raff, Amit Sheth, Srinivasan Parthasarathy, Manas Gaur. 2024. Abstention vs. Hallucination: Benchmarking LLM Source Attribution for Scientific Citations (REASONS). arXiv:2405.02228. https://arxiv.org/abs/2405.02228
10. Venktesh V, Abhijit Anand, Avishek Anand, Vinay Setty. 2024. QuanTemp: A Real-World Open-Domain Benchmark for Fact-Checking Numerical Claims. SIGIR 2024. arXiv:2403.17169. https://arxiv.org/abs/2403.17169
11. Andreas Vlachos, Sebastian Riedel. 2015. Identification and Verification of Simple Claims about Statistical Properties. EMNLP 2015. https://eprints.whiterose.ac.uk/91378/

## Appendix A: Limitations and Dual-Use / Ethical Considerations

**What the result establishes and what it does not.** For one sample of Hindi news on six central schemes, the study establishes how often a numerical claim can be linked to a dated official figure in a fixed list of central sources, how often the two agree, and how one free LLM verifier behaves on these claims with and without official evidence. It does not establish whether any outlet is accurate in general, whether the official figures are true, whether any journalist or official intended to mislead, or how other models or later versions behave. A mismatch is a measurement outcome under stated rules and may come from a date lag, a definition difference or rounding. An "unbindable" label means we did not find public evidence in the listed sources, not that the claim is false.

**How the dataset or a binding tool could be misused.** *Selective attacks on outlets:* a list of mismatches could be cherry-picked to discredit one newspaper or one government; we publish aggregate rates and every claim with its evidence, including all the matches, and describe mismatches as measurement outcomes, not accusations. *Treating official numbers as truth:* a "match" label could be presented as proof that a claim is true; binding checks consistency with official figures, not ground truth. *Gaming:* publishers could phrase claims vaguely ("करोड़ों लोगों को लाभ") so they stay unbindable; a vague-claim rate, not measured here, would make such a shift visible. *Over-trust in AI verifiers:* without evidence the tested verifier cited official-looking sources that do not show the figure, and with evidence it sometimes declared a claim contradicted by a figure for a different place or metric. Neither the dataset nor any tool built on it should be presented as an automatic truth checker, and an automated "mismatch" should never be published as an accusation without human review. *Political neutrality:* schemes were chosen by news coverage volume, not by party, and every claim is tagged by speaker.

**Personal data and source handling.** We collected news articles and aggregate scheme statistics only; no personal data was collected. Several scheme portals expose beneficiary-level lists; these were never opened, scraped or stored. Crawling was polite (a 3-second delay between requests, robots.txt respected). Outlets that disallowed or refused the crawler were excluded. Raw pages were cached locally only to confirm that each claim clause and evidence quote appears verbatim; the release contains only the URL, date, headline and claim clause, not full articles. The evidence excerpts are short passages from public government pages. The verifier used a free API key; no personal data was sent to the model.

## Appendix B: Verifier Prompts (as used)

### B.1 Closed-book prompt (C1)

The exact prompt sent for each closed-book call (scripts/run_verifier.py). {scheme} is the scheme's full name, {claim} the verbatim Hindi clause or its English gloss, and {date} the article date. The request set temperature 0 and a JSON response type.

```
You check numerical claims about Indian government schemes against official statistics.
SCHEME: {scheme}
CLAIM: {claim}
ARTICLE DATE: {date}
Answer in JSON only, with exactly these keys:
{"verdict": "SUPPORTED" | "CONTRADICTED" | "CANNOT_VERIFY",
 "source_title": <title of the official source you rely on, or null>,
 "source_url": <official URL you rely on, or null>,
 "official_figure": <the official number as a plain number in the claim's unit, fully
   written out (for example 94900000, not "9.49 crore"; a percentage as 82.09), or null>,
 "as_of_date": <date the official figure refers to, YYYY-MM-DD, or null>,
 "confidence": <number from 0 to 1: how likely your verdict is correct>,
 "reason": <one sentence>}
SUPPORTED means an official source states a figure that agrees with the claim.
CONTRADICTED means an official source states a different figure for the same metric,
place and period. If you are not certain an official source states this exact figure,
answer CANNOT_VERIFY with null source and figure. Do not guess a URL.
```

Long lines are wrapped here for the page; in the prompt the "official_figure" line and the final paragraph are single lines. Example of a filled claim line (C001, Hindi): "CLAIM: 3.15 लाख करोड़ रुपये का प्रावधान किया गया है"; English: "CLAIM: An outlay of Rs 3.15 lakh crore has been provided for the extension of the scheme."

### B.2 Evidence-given prompt (C2)

The exact prompt sent for each evidence-given call (scripts/run_evidence.py), with the same request settings. {figure} is the claim's number as written in the Hindi clause, or its English form with the hedge (for example "more than 9.49 crore farmers"); {evidence} is the frozen excerpt block. Instructions and evidence are identical for both languages; only the claim and the figure change.

```
You check a numerical claim about an Indian government scheme against an excerpt from
official pages.
Use only the evidence below. Do not use outside knowledge.
SCHEME: {scheme}
CLAIM: {claim}
FIGURE TO CHECK: {figure}
ARTICLE DATE: {date}
EVIDENCE:
{evidence}

Labels:
MATCH: the evidence states a figure for the same metric, place and period, and it agrees
with the claim at the precision the claim states ("more than X" agrees if the official
figure is at least X; "about X" agrees within 5%).
MISMATCH: the evidence states a figure for the same metric, place and period, and it does
not agree.
AMBIGUOUS: the evidence states a figure for this or a closely related metric, but it cannot
settle the claim: a different definition or scope, a date more than about one month from
the time the claim refers to, several official figures that disagree, or an official
figure too imprecise to test the claim.
CANNOT_VERIFY: the evidence does not state a figure for this metric and place.
Answer in JSON only, with exactly these keys:
{"label": "MATCH" | "MISMATCH" | "AMBIGUOUS" | "CANNOT_VERIFY",
 "official_figure": <the official figure from the evidence you compared with the claim, as
   a plain number in the claim's unit, fully written out (for example 94900000, not
   "9.49 crore"; a percentage as 82.09), or null>,
 "as_of_date": <the date that official figure refers to, YYYY-MM-DD, or null>,
 "evidence_quote": <the shortest exact phrase from the evidence that states that figure,
   or null>,
 "confidence": <number from 0 to 1: how likely your label is correct>,
 "reason": <one sentence>}
```

Long lines are wrapped here for the page; in the prompt the first line, each label definition and each JSON key line are single lines. Each official page in {evidence} is given as a header (page URL, the page's date line or "none (live dashboard page)", and the retrieval date) followed by the excerpt between "<<<" and ">>>", with "[...]" between separate windows from the same page.

## Appendix C: Further Tables

TABLE: **Table C.1.** Labels by outlet (strict rule). Brackets give the count and Wilson 95% CI.
| Outlet | Match | Mismatch | Ambiguous | Unbindable | Total | Coverage | Strict match rate |
|---|---|---|---|---|---|---|---|
| Prabhat Khabar | 11 | 1 | 10 | 20 | 42 | 52.4% (22/42, 37.7-66.6) | 91.7% (11/12, 64.6-98.5) |
| Aaj Tak | 5 | 0 | 5 | 16 | 26 | 38.5% (10/26, 22.4-57.5) | 100.0% (5/5, 56.6-100.0) |
| Patrika | 3 | 2 | 3 | 14 | 22 | 36.4% (8/22, 19.7-57.0) | 60.0% (3/5, 23.1-88.2) |
| Amar Ujala | 3 | 0 | 3 | 6 | 12 | 50.0% (6/12, 25.4-74.6) | 100.0% (3/3, 43.8-100.0) |

TABLE: **Table C.2.** Labels by speaker (strict rule).
| Speaker | Match | Mismatch | Ambiguous | Unbindable | Total | Coverage | Strict match rate |
|---|---|---|---|---|---|---|---|
| Journalist | 15 | 2 | 17 | 36 | 70 | 48.6% (34/70, 37.2-60.0) | 88.2% (15/17, 65.7-96.7) |
| State government | 2 | 0 | 3 | 8 | 13 | 38.5% (5/13, 17.7-64.5) | 100.0% (2/2, 34.2-100.0) |
| Government | 3 | 0 | 1 | 5 | 9 | 44.4% (4/9, 18.9-73.3) | 100.0% (3/3, 43.8-100.0) |
| State minister | 1 | 0 | 0 | 6 | 7 | 14.3% (1/7, 2.6-51.3) | 100.0% (1/1, 20.7-100.0) |
| Official | 1 | 1 | 0 | 0 | 2 | 100.0% (2/2, 34.2-100.0) | 50.0% (1/2, 9.5-90.5) |
| Opposition | 0 | 0 | 0 | 1 | 1 | 0.0% (0/1, 0.0-79.3) | n/a |

TABLE: **Table C.3.** The three strict mismatches, largest gap first. Official values with the as-of date of the official figure; all three official figures are from PIB. For C093 the PIB note gives 9.34 crore and also "more than 9.34 crore", a lower bound; we use 9.34 crore, which the headline and text state, and "about 10 crore" would pass the ±5% rule only if the true count were at least 9.524 crore. Treating C093 as ambiguous instead would make the strict match rate 22/24 (91.7%).
| Claim | Outlet, date | Claimed (Hindi) | Claimed value | Official (as of) | Gap | Lenient |
|---|---|---|---|---|---|---|
| C092 | Patrika, 2026-10-30 | 447 लाख करोड़ रुपये से अधिक | 447,000,000,000,000 | 4,470,000,000,000 (2026-07-31) | +9900.0% | mismatch |
| C093 | Patrika, 2026-10-30 | करीब 10 करोड़ | 100,000,000 | 93,400,000 (2026-10-30) | +7.1% | mismatch |
| C086 | Prabhat Khabar, 2026-10-30 | 18,700 करोड़ | 187,000,000,000 | 186,900,000,000 (2026-10-30) | +0.1% | match |

TABLE: **Table C.4.** The 12 ambiguous claims whose number would fail the strict rule against the nearest official figure. They are not counted as mismatches because the period or definition differs.
| Claim | Scheme | Date | Claimed | Official (as of) | Gap | Reason |
|---|---|---|---|---|---|---|
| C046 | PM-JAY | 2026-09-23 | 39,000 से ज्यादा | 38,000 (2026-08-31) | +2.6% | Official figure imprecise: PIB says "over 38,000" hospitals. |
| C031 | PMAY | 2026-08-23 | 20 लाख 40 हजार | 2,082,891 (2026-11-14) | -2.1% | Period gap: only a live report 83 days after the claim. |
| C082 | PM-JAY | 2026-10-29 | 13.5 करोड़ | 132,500,000 (2026-08-31) | +1.9% | Definition and period: people treated against admissions, 59 days earlier. |
| C061 | JJM | 2026-10-03 | 34.94 लाख | 3,451,000 (2026-03-03) | +1.2% | Period gap: official figure 214 days earlier. |
| C032 | JJM | 2026-09-03 | 34.87 लाख | 3,451,000 (2026-03-03) | +1.0% | Period gap: 184 days; dashboard is JavaScript-only. |
| C068 | JJM | 2026-10-14 | 82.52% | 82.09 (2026-07-18) | +0.5% | Period gap: latest dated national figure. |
| C063 | JJM | 2026-10-03 | 82.47 प्रतिशत | 82.09 (2026-07-18) | +0.5% | Period gap: latest dated national figure. |
| C052 | PMAY | 2026-09-28 | 3.11 करोड़ | 31,200,000 (2026-08-07) | -0.3% | Period gap; claim is below the earlier official figure. |
| C051 | PMAY | 2026-09-28 | 3.92 करोड़ | 39,100,000 (2026-08-07) | +0.3% | Period gap: no official figure within 31 days. |
| C044 | PM-JAY | 2026-09-23 | 48.54 करोड़ से ज्यादा | 485,100,000 (2026-09-21) | +0.1% | Definition: cards against people holding cards. |
| C060 | JJM | 2026-10-03 | 62.51 लाख | 6,253,000 (2026-03-03) | -0.0% | Period gap: official figure 214 days earlier. |
| C036 | JJM | 2026-09-06 | 81.57% | 81.56 (2026-01-28) | +0.0% | Conflicting official figures: PIB releases give 81.56% and 81.57%. |

TABLE: **Table C.5.** The seven PIB release IDs cited by the closed-book verifier (all 7 PIB citations; 7 distinct IDs). Each number exists, but the release it opens is unrelated to the claim. Actual titles were fetched from pib.gov.in on 14 November 2026 and are given in English translation.
| Claim | Source title given by the model | Release actually at that ID |
|---|---|---|
| C002 (hi) | PM-KISAN: Over Rs 3.42 lakh crore transferred to more than 11 crore farmers ... | Weekly Holi special train between Lokmanya Tilak Terminus and Prayagraj (Hindi) |
| C029 (en) | Cabinet Decisions on Pradhan Mantri Awas Yojana | Shri Pralhad Joshi takes charge of the Ministry of New and Renewable Energy (Punjabi) |
| C043 (en) | Ayushman Bharat PM-JAY crosses 6 crore hospital admissions | English rendering of the Prime Minister's speech to the Indian community in Warsaw, Poland (Kannada) |
| C057 (en) | Cabinet Committee on Economic Affairs approval for continuation of PMUY | Indian Sign Language centre to celebrate Sign Language Day on 23 September 2023 (Hindi) |
| C081 (hi) | Ayushman Bharat PM-JAY Official Website / PIB | PM GatiShakti network planning group evaluates infrastructure projects (Manipuri) |
| C081 (en) | Ayushman Bharat PM-JAY reaches a major milestone of 6 crore hospital admissions | Complementary feeding for healthy child growth, a theme of Poshan Maah 2024 (Malayalam) |
| C092 (en) | Press Information Bureau Release on PM-KISAN | Prime Minister greets on the Sikh New Year (Hindi) |

TABLE: **Table C.6.** Calibration of all 204 closed-book answers (both languages) by stated confidence. Bins include the lower bound and exclude the upper one (the last bin includes 1.0). "Correct" means the verdict equals the expected verdict; ECE = sum over bins of (answers / 204) × |mean confidence − share correct| = 0.517, a rough figure since two bins hold 195 of the 204 answers.
| Stated confidence | Answers | Mean confidence | Verdict correct | Of which CANNOT_VERIFY |
|---|---|---|---|---|
| 0.00-0.50 | 85 | 0.00 | 77.6% (66/85, 67.7-85.2) | 85 |
| 0.50-0.80 | 1 | 0.50 | 100.0% (1/1, 20.7-100.0) | 1 |
| 0.80-0.90 | 4 | 0.80 | 100.0% (4/4, 51.0-100.0) | 3 |
| 0.90-0.95 | 4 | 0.90 | 75.0% (3/4, 30.1-95.4) | 2 |
| 0.95-1.00 | 110 | 0.995 | 65.5% (72/110, 56.2-73.7) | 97 |

TABLE: **Table C.7.** Binding labels by scheme (strict rule). Coverage = any binding (match + mismatch + ambiguous) / all claims; match rate = match / (match + mismatch). Brackets give the count and Wilson 95% CI.
| Scheme | Match | Mismatch | Ambiguous | Unbindable | Total | Coverage | Strict match rate |
|---|---|---|---|---|---|---|---|
| PM-KISAN | 8 | 3 | 2 | 14 | 27 | 48.1% (13/27, 30.7-66.0) | 72.7% (8/11, 43.4-90.3) |
| PM-JAY | 2 | 0 | 5 | 16 | 23 | 30.4% (7/23, 15.6-50.9) | 100.0% (2/2, 34.2-100.0) |
| JJM | 1 | 0 | 8 | 12 | 21 | 42.9% (9/21, 24.5-63.5) | 100.0% (1/1, 20.7-100.0) |
| PMAY | 8 | 0 | 6 | 4 | 18 | 77.8% (14/18, 54.8-91.0) | 100.0% (8/8, 67.6-100.0) |
| MGNREGA | 2 | 0 | 0 | 7 | 9 | 22.2% (2/9, 6.3-54.7) | 100.0% (2/2, 34.2-100.0) |
| PMUY | 1 | 0 | 0 | 3 | 4 | 25.0% (1/4, 4.6-69.9) | 100.0% (1/1, 20.7-100.0) |
| **All** | **22** | **3** | **21** | **56** | **102** | **45.1% (46/102, 35.8-54.8)** | **88.0% (22/25, 70.0-95.8)** |

TABLE: **Table C.8.** Closed-book results by language (gemini-3.5-flash-lite, temperature 0, one run); 204 answers = 102 claims × Hindi and English. Wilson 95% CI for the pooled column.
| Measure | Hindi | English | Both |
|---|---|---|---|
| Verdict agrees with gold label | 73.5% (75/102) | 69.6% (71/102) | 71.6% (146/204, 65.0-77.3) |
| CANNOT_VERIFY on unbindable claims | 96.4% (54/56) | 91.1% (51/56) | 93.8% (105/112, 87.7-96.9) |
| CANNOT_VERIFY on cleanly bound claims | 88.0% (22/25) | 96.0% (24/25) | 92.0% (46/50, 81.2-96.8) |
| CANNOT_VERIFY on ambiguous claims | 85.7% (18/21) | 90.5% (19/21) | 88.1% (37/42, 75.0-94.8) |
| Committed answers (verdict right) | 8 (3 right) | 8 (1 right) | 16 (4 right, 25.0%, 10.2-49.5) |
| Always-CANNOT_VERIFY baseline | 75.5% (77/102) | 75.5% (77/102) | 75.5% (154/204, 69.2-80.9) |

TABLE: **Table C.9.** Evidence-given results by language (gemini-3.5-flash-lite, temperature 0, one run); 202 answers = 101 claims × Hindi and English. Wilson 95% CI for the pooled column.
| Measure | Hindi | English | Both |
|---|---|---|---|
| Label equals gold label (4 labels) | 67.3% (68/101) | 70.3% (71/101) | 68.8% (139/202, 62.1-74.8) |
| MATCH on bound + match | 95.5% (21/22) | 100.0% (22/22) | 97.7% (43/44, 88.2-99.6) |
| MISMATCH on bound + mismatch | 2/3 | 2/3 | 66.7% (4/6, 30.0-90.3) |
| AMBIGUOUS on bound-ambiguous | 0.0% (0/21) | 0.0% (0/21) | 0.0% (0/42, 0.0-8.4) |
| CANNOT_VERIFY on near-miss excerpts | 81.8% (45/55) | 85.5% (47/55) | 83.6% (92/110, 75.6-89.4) |
| False MATCH on near-miss excerpts | 1/55 | 1/55 | 1.8% (2/110, 0.5-6.4) |
| MISMATCH on near-miss excerpts | 9/55 | 6/55 | 13.6% (15/110, 8.4-21.3) |
| False abstention on cleanly bound claims | 0/25 | 0/25 | 0.0% (0/50, 0.0-7.1) |

Article and official URLs for every row of Tables C.3 and C.4 are in report/tables.md; every closed-book answer and URL check is in report/verifier_tables.md; every evidence-given count is in report/evidence_tables.md.

## LLM Usage Statement

AI assistants were used to help write code, collect and organise data, and edit the text. The author designed the study, set the labelling rules, and is responsible for all content. Gemini (gemini-3.5-flash-lite) was used only as the system under test in Sections 4.3 to 4.5.

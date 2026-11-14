# Saboot: How Much of Hindi News About Government Schemes Can Be Bound to Official Numbers, and Does an LLM Verifier Know When It Can't?

AUTHOR: Wageesha Tripathi | Independent, Varanasi, India | tripathiwageesha2002@gmail.com

ABSTRACT: Hindi newspapers report government schemes in numbers, and readers, fact-checkers and AI research agents need to know whether those numbers agree with official statistics. We collected 102 numerical claims about six central schemes from four Hindi outlets (August to November 2026) and searched official releases, dashboards and Parliament answers for a dated official figure for each. Only 45.1% of claims (46/102, 95% CI 35.8-54.8%) could be bound to an official statistic and 24.5% cleanly; coverage was 69.2% for national claims but 20.0% for state-level claims. Of the 25 cleanly bound claims, 88.0% matched. We then asked a free LLM verifier (gemini-3.5-flash-lite, closed-book) to check every claim in Hindi and English. It answered "cannot verify" on 92.2% of 204 answers (102 claims × 2 languages), but almost as often on claims with official evidence (92.0%) as on unbindable ones (93.8%), and its verdict accuracy (71.6%) was below an always-abstain baseline (75.5%). Its 16 committed answers were right 4 times, and none of the sources it cited showed the stated figure: all 7 PIB release IDs it cited open unrelated releases, one of them a Holi special train. Hindi and English wording gave the same verdict on 90.2% of claims. This is an exploratory, single-annotator, AI-assisted dataset and a diagnostic case study of one model. In this domain "cannot verify" is often the right answer, but a high abstention rate does not show that a verifier can tell checkable claims from uncheckable ones.

## 1. Introduction

Hindi newspapers report government schemes in numbers every day: how many farmers received a PM-KISAN instalment, how many houses PMAY has completed, how many households have a tap connection. For many readers these articles are the main way they learn whether a scheme is working. Most of these numbers have an official counterpart: dated Press Information Bureau (PIB) releases in Hindi and English, scheme dashboards, and Parliament answers. Few people check: the sources are scattered, often in English, and dashboards show "as on today" values that overwrite last month's figure. AI agents that research on people's behalf are now asked "is this number right?" as well. When no official figure can be found, the honest answer is "I cannot verify this". The failure we care about is an agent that names a plausible official source that does not exist or does not say what is claimed, so that an unchecked claim looks checked.

We call the act of linking a claim to a specific, dated official statistic **binding**. Before one can judge a verifier in this domain, one needs to know how much of the domain is bindable at all and what the correct answer is for each claim. This paper measures that, then tests one LLM verifier against it. Our research questions are:

- **RQ1 Coverage.** What fraction of numerical claims about central schemes in Hindi news can be bound to a dated official statistic?
- **RQ2 Agreement.** Of the claims that can be bound cleanly, how often does the number match?
- **RQ3 Verifier behaviour.** Without evidence, does an LLM verifier say "cannot verify" when no official figure exists, commit when one does, and cite real sources when it commits?
- **RQ4 Language.** Does the verifier answer differently for the Hindi and the English wording of the same claim?

**Our main contributions are:**

1. A dataset of 102 real numerical claims from four Hindi outlets, each bound to a dated official source with a verbatim quote, or marked unbindable with the reason.
2. A binding study of this domain: how many claims are cleanly bound, ambiguously bound or unbindable, by scheme, outlet, geography and speaker, and how often bound claims agree.
3. A closed-book evaluation of a free LLM verifier on all 102 claims in Hindi and English (204 answers), scored against these labels, with an automatic check of every URL it cited.

## 2. Related Work

**Numerical fact-checking.** Vlachos and Riedel (2015) checked simple statistical claims against a knowledge base with approximate numeric matching. QuanTemp (Venktesh et al., 2024) collected 15,514 real numerical and temporal claims, in English, with web-snippet evidence. The CLEF-2026 CheckThat! lab (Struß et al., 2026) covers numerical claims in English, Spanish and Arabic, not Hindi. NumPert (Aarnes and Setty, 2025) perturbs numbers to probe the robustness of LLM veracity predictions.

**Claims over tables and databases.** The closest work, Devasier et al. (2026), generates synthetic claims from OECD tables in four languages including Hindi; the claims are synthetic and the evidence is not Indian government data. ClaimDB (Theologitis et al., 2026) verifies claims over large real databases and finds that models struggle to abstain; it is English and not tied to news.

**Indian-language claim verification.** IndicClaimBuster (Pal et al., 2025) offers about 9,000 claims from Indian news in English, Hindi, Bengali and code-mixed text, and the IndicClaimVer shared task at FIRE 2026, co-organised by its first author, benchmarks claim verification in major Indian languages. HiFACTMix (Thakur et al., 2025) has 1,500 code-mixed Hinglish political claims, and X-FACT (Gupta and Srikumar, 2021) is a multilingual benchmark. None focus on numbers or use official statistics as evidence.

**Abstention versus hallucination.** REASONS (Tilwani et al., 2024) benchmarks whether LLMs abstain or hallucinate when attributing scientific citations; we ask the same of official statistical sources. **Gap:** we found no work that measures, on real Hindi news, how much numerical content can be bound to government statistics, how often it agrees, and whether a verifier's abstentions follow that boundary.

## 3. Methods

### 3.1 Claim sampling

We studied six central schemes chosen by volume of news coverage, not by political association: PM-KISAN, PMAY (Gramin and Urban as one scheme), PM Ujjwala (PMUY), Jal Jeevan Mission (JJM), Ayushman Bharat PM-JAY and MGNREGA, aiming at 100 claims. Two of the three planned outlets (Dainik Jagran, Navbharat Times) and several others refused the study's crawler; we did not circumvent refusals, kept Amar Ujala and added Patrika, Prabhat Khabar and Aaj Tak, whose robots.txt files allow it. Articles from 1 August to 13 November 2026 were found by site-restricted search and tag pages, and every fetch was logged. Only India-level and state-level claims were kept.

A claim is one sentence or clause with a number tied to a central scheme metric (beneficiaries, houses, connections, amount disbursed, person-days, coverage or budget). We excluded bare dates and instalment ordinals, state-only schemes, future targets and fixed entitlements set by scheme rules. Duplicates (same number, scheme, metric and geography within 7 days) were dropped. Each claim records outlet, URL, date, the verbatim Hindi clause, an English gloss, the normalised number (1 लाख = 100,000, 1 करोड़ = 10,000,000, stated precision kept), scheme, metric, geography, period, hedge and speaker; a script confirmed every clause verbatim in the stored article.

### 3.2 Labels and binding rules

Each claim received one of four labels. **Bound + match**: an official dated source reports the same metric, geography and period, and the number agrees under the match rule. **Bound + mismatch**: same metric, geography and period, but the number disagrees beyond the rule. **Bound-ambiguous**: official numbers exist but cannot be aligned without a judgement call (a different definition, a period gap, or conflicting official figures). **Unbindable**: no official figure for the same metric and geography was found in the listed sources.

Sources were searched in a fixed order: PIB in the claim's language, PIB in the other language, the scheme dashboard or its Wayback Machine snapshot, and Parliament answers, stopping at the first source with the same metric and geography, preferring the nearest date on or before the article date. For a cumulative stock (houses completed, tap connections) the official date had to be within 31 days either side of the claim's time reference; if the only official figure was further away, earlier or later, the claim was labelled bound-ambiguous (period gap) with both dates recorded. **Match rule:** the official value, rounded to the claim's stated precision, must equal the claim. Hedged claims follow their hedge: "से अधिक" (over) requires official ≥ claim, and "लगभग" or "करीब" (about) allows ±5%. The lenient rule also accepts a gap of up to 5%. These rules were written down before any label was assigned.

### 3.3 Validation and provenance

This is an exploratory, single-annotator, AI-assisted dataset, not independently validated ground truth. An AI agent (Claude, run in Claude Code on the author's laptop) found the articles, chose the claims, searched the official sources and recorded each figure, date, URL and verbatim quote with a rationale, under the rules above, written before labelling (data/labelling-rules.md); a script applied the match rule. Every official page behind a binding was then opened in a browser and checked against the recorded source: the figure and scope agreed for all 46 bound or ambiguous claims and the as-of date for 36, and ten bindings were corrected (one label; five had recorded a release date instead of the date the page gives for the figure). A script found all 73 recorded evidence quotes, from 19 official pages, verbatim in the saved page text. These checks confirm that the recorded evidence is on the page, not that every alignment judgement is right; claim selection and classification may carry the agent's bias, and there was no second human labeller. All labels were fixed before any verifier call.

### 3.4 Verifier experiment

**Model.** We used the Gemini API free tier. The planned gemini-2.5-flash and gemini-2.5-flash-lite returned HTTP 404 ("no longer available to new users") on 14 November 2026; of the named replacements, gemini-3.8-flash returned HTTP 503 (overloaded) on repeated attempts and answered only one call, so it is excluded. All results are for **gemini-3.5-flash-lite**, which answered all 204 calls (102 claims, each in Hindi and English) on 14 November 2026, at temperature 0, one run.

**Condition.** Only the closed-book condition of the three planned ones was run (gold-evidence and distractor conditions were cut). The model saw the scheme name, the claim and the article date, and returned a verdict (SUPPORTED, CONTRADICTED or CANNOT_VERIFY), the official source title and URL, the official figure and its date, a confidence from 0 to 1 and a reason, and was told to answer CANNOT_VERIFY unless certain and not to guess a URL (Appendix B). The instructions were in English; only the claim text changed (the Hindi clause or its English gloss).

**Scoring.** The expected verdict is SUPPORTED for bound + match, CONTRADICTED for bound + mismatch, and CANNOT_VERIFY for ambiguous and unbindable claims, which have no clean official figure. Every distinct cited URL was requested once (3 seconds apart) and non-PIB pages were also opened in a browser. Following the protocol, a cited source **fails** when the URL does not load, loads but does not show the stated figure, or is not an official government domain (the cited-source failure rate); for PIB we checked that the release ID exists and that its title names the claim's scheme. Hindi and English answers are compared per claim with an exact McNemar test.

### 3.5 Metrics

Coverage = (match + mismatch + ambiguous) / all claims; strict coverage = (match + mismatch) / all. Match rate = match / (match + mismatch). Proportions carry counts and Wilson 95% intervals; these treat claims as independent, which they are not fully, since several claims come from the same article, so the intervals are optimistic. All numbers are computed by scripts/report_tables.py and scripts/score_verifier.py from the data files.

## 4. Results

### 4.1 The sample and coverage (RQ1)

We attempted 79 article fetches (73 succeeded). After removing 21 duplicates, the dataset has 102 claims from 37 articles (2 August to 11 November 2026): 42 from Prabhat Khabar, 26 Aaj Tak, 22 Patrika and 12 Amar Ujala; 52 national and 50 state-level; 70 in the journalist's own words. Coverage was 45.1% (46/102, 95% CI 35.8-54.8%) and strict coverage 24.5% (25/102, CI 17.2-33.7%); 20.6% (21/102) were bound only ambiguously and 54.9% (56/102) were unbindable (Table 1).

The largest difference is by geography. National claims had 69.2% coverage (36/52, CI 55.7-80.1%) and state claims 20.0% (10/50, CI 11.2-33.0%); 40 of the 50 state claims were unbindable, and the intervals do not overlap. The recorded reasons concern where figures are available within our searched source set (search effort was not logged): state-wise PM-KISAN instalment figures were not in any central source, the JJM dashboard loads its state rows by JavaScript, and state-government releases were outside the source list. By outlet, coverage ranged from 36.4% to 52.4% with overlapping intervals (Appendix C). The 21 ambiguous claims carry 25 recorded reasons, as four have two: period gap (13), conflicting official figures (5), definition difference (5) and an imprecise official figure ("over 38,000", 2).

TABLE: **Table 1.** Binding labels by scheme (strict rule). Coverage = any binding (match + mismatch + ambiguous) / all claims; match rate = match / (match + mismatch). Brackets give the count and Wilson 95% CI.
| Scheme | Match | Mismatch | Ambiguous | Unbindable | Total | Coverage | Strict match rate |
|---|---|---|---|---|---|---|---|
| PM-KISAN | 8 | 3 | 2 | 14 | 27 | 48.1% (13/27, 30.7-66.0) | 72.7% (8/11, 43.4-90.3) |
| PM-JAY | 2 | 0 | 5 | 16 | 23 | 30.4% (7/23, 15.6-50.9) | 100.0% (2/2, 34.2-100.0) |
| JJM | 1 | 0 | 8 | 12 | 21 | 42.9% (9/21, 24.5-63.5) | 100.0% (1/1, 20.7-100.0) |
| PMAY | 8 | 0 | 6 | 4 | 18 | 77.8% (14/18, 54.8-91.0) | 100.0% (8/8, 67.6-100.0) |
| MGNREGA | 2 | 0 | 0 | 7 | 9 | 22.2% (2/9, 6.3-54.7) | 100.0% (2/2, 34.2-100.0) |
| PMUY | 1 | 0 | 0 | 3 | 4 | 25.0% (1/4, 4.6-69.9) | 100.0% (1/1, 20.7-100.0) |
| **All** | **22** | **3** | **21** | **56** | **102** | **45.1% (46/102, 35.8-54.8)** | **88.0% (22/25, 70.0-95.8)** |

FIGURE: report/figures/fig1_labels_by_scheme_geography.png | 4.4 | **Figure 1.** Binding labels for the 102 claims (strict rule), by scheme (top) and by geography (bottom). Numbers inside bars are claim counts; n is the number of claims per row. Ambiguous means official figures exist but use a different definition or period.

### 4.2 Agreement (RQ2)

Among the 25 cleanly bound claims, the strict match rate was 88.0% (22/25, CI 70.0-95.8%) and the lenient match rate 92.0% (23/25, CI 75.0-97.8%). All three strict mismatches concern the 24th PM-KISAN instalment, reported on 30 October 2026, and two come from the same article (Table C.3). They are a unit slip (447 lakh crore against an official 4.47 lakh crore), a hedge used too widely ("about 10 crore" farmers against an official 9.34 crore, 7.1% high, outside the ±5% band), and a rounding difference (18,700 crore against Rs 18,690 crore, which matches under the lenient rule). Twelve of the 21 ambiguous claims would also fail the strict rule against the nearest official figure, but all twelve lie within 2.6% of it, and most are cumulative totals compared with an official value dated weeks or months away (Table C.4).

### 4.3 Verifier behaviour (RQ3)

All 204 answers from gemini-3.5-flash-lite were valid JSON. The model answered CANNOT_VERIFY on 188 of 204 (92.2%) and committed (SUPPORTED or CONTRADICTED) on 16 (Figure 2, Table 2).

FIGURE: report/figures/fig2_verifier_verdicts.png | 5.0 | **Figure 2.** Closed-book verdicts of gemini-3.5-flash-lite for the 102 claims, by gold label, for the Hindi clause (top) and its English gloss (bottom). Grey is CANNOT_VERIFY. The correct answer is SUPPORTED for match, CONTRADICTED for mismatch, and CANNOT_VERIFY for ambiguous and unbindable claims.

**Abstention did not follow bindability.** On unbindable claims the model abstained 93.8% of the time (105/112 answers, CI 87.7-96.9%), which is the desired behaviour. But it abstained almost as often on cleanly bound claims, 92.0% (46/50, CI 81.2-96.8%), where a dated official figure exists. Its overall verdict accuracy was 71.6% (146/204, CI 65.0-77.3%), slightly below the 75.5% (154/204) that a verifier answering CANNOT_VERIFY to everything would score on this set. On the 50 answers for cleanly bound claims, the verdict was right 4 times (8.0%, CI 3.2-18.8%). Half of the abstentions (94/188) gave as their reason that the article date was "in the future", A plausible explanation, which we did not test, is that the 2026 dates fall after the model's training data.

**When it committed, it was mostly wrong, and its sources did not back it.** Of the 16 committed answers, 7 were for unbindable claims and 5 for ambiguous ones; the verdict was right on 4 (25.0%, CI 10.2-49.5%). In 10 of the 16, the "official figure" it reported was exactly the number in the claim, and 12 of 16 gave an as-of date before 2026 although every claim is from August to November 2026. Where an official figure exists in our data (9 answers), the model's figure was exact in 3 and within 5% in 2 more; the other 4 were off by 21.7% or more, including a figure 90% too low (C047) on a claim it nevertheless marked SUPPORTED, and a different metric altogether (C046). 

**Every cited source failed the check.** All 16 committed answers cited a source (12 distinct URLs), and none showed the stated figure. All 7 cited PIB links used release IDs that exist, but each belongs to an unrelated release, often in another language: a Holi special train, a Sikh New Year greeting, a minister taking charge of a different ministry, a speech in Warsaw, and three more (Table C.5). Five answers cited a scheme portal's home page, which loaded but did not show the figure, and 4 cited two PM-JAY addresses that did not load from our network, either by plain request or in a browser. The cited-source failure rate (Section 3.4) was therefore 100% (16/16, CI 80.6-100%): the page cited in 12 of the 16 answers loaded, and none of these 12 showed the stated figure. A narrower test of non-resolving or non-official URLs alone gives 25.0% (4/16) and would miss every wrong PIB citation. The one answer with both a correct verdict and a correct figure (C002, Hindi) cited the Holi train release.

TABLE: **Table 2.** Verifier results (gemini-3.5-flash-lite, closed-book, temperature 0, one run). Counts with Wilson 95% CI; the 204 answers are 102 claims × Hindi and English.
| Measure | Hindi | English | Both |
|---|---|---|---|
| Verdict agrees with gold label | 73.5% (75/102) | 69.6% (71/102) | 71.6% (146/204, 65.0-77.3) |
| CANNOT_VERIFY on unbindable claims | 96.4% (54/56) | 91.1% (51/56) | 93.8% (105/112, 87.7-96.9) |
| CANNOT_VERIFY on cleanly bound claims | 88.0% (22/25) | 96.0% (24/25) | 92.0% (46/50, 81.2-96.8) |
| CANNOT_VERIFY on ambiguous claims | 85.7% (18/21) | 90.5% (19/21) | 88.1% (37/42, 75.0-94.8) |
| Committed answers (verdict right) | 8 (3 right) | 8 (1 right) | 16 (4 right, 25.0%, 10.2-49.5) |
| Always-CANNOT_VERIFY baseline | 75.5% (77/102) | 75.5% (77/102) | 75.5% (154/204, 69.2-80.9) |

**Calibration.** Committed answers had a mean stated confidence of 0.94 but were right 25.0% of the time. Of the 110 answers with confidence 0.95 or more (97 of them abstentions), 65.5% were right. Abstentions mostly carried a confidence of 0 (85 answers) or 0.95 and above (97 answers), so the number does not separate certain from uncertain answers; the expected calibration error over five unequal bins was 0.52 (Table C.6), a rough figure given that two bins hold 195 of the 204 answers.

### 4.4 Hindi versus English (RQ4)

The Hindi clause and the English gloss gave the same verdict on 90.2% of claims (92/102, CI 82.9-94.6%). The verdict was right in both languages for 68 claims, only in Hindi for 7, only in English for 3, and in neither for 24 (exact McNemar test, p = 0.34). The model committed on 8 claims in each language but on only 3 of the same claims (C034, C081, C092). With 10 discordant pairs this run cannot show a language difference; the main observation is that the committed answers are unstable across wordings of the same fact.

## 5. Discussion and Limitations

**Coverage reflects what our searched sources publish, and bound numbers usually agree.** Fewer than half of the claims (45.1%) could be bound, a quarter cleanly, and mostly national ones. Central sources publish national totals in dated releases, but state-level figures were often not published centrally, sat behind JavaScript dashboards, or were overwritten by live values. The useful fix is on the publishing side: dated, archived, state-wise and definition-labelled releases. When a number could be bound it usually matched (88.0%, CI 70.0-95.8%), and the three mismatches were a unit slip, a stretched hedge and a rounding difference, not competing figures.

**A high abstention rate is not the same as knowing when to abstain.** The binding study gives a reference for what a careful verifier should do: say "cannot verify" on 56 of 102 claims, and on 40 of 50 state claims. The tested model said it on nearly everything, so it seldom invented a verdict; measured by abstention rate alone it would look safe. But it did not separate checkable from uncheckable claims, and a blanket abstainer would have scored higher. The few times it committed show the failure mode that matters for AI research agents: confident verdicts that repeat the claim's own number, refer to older dates, and cite official-looking sources that do not show the figure, so that an unchecked claim looks checked. These closed-book results describe one model, not general capability, and do not show that retrieval would fix the problem; an evaluation in this domain needs abstention rates split by whether evidence exists, plus a check of every cited source.

### Limitations

- **No second human labeller:** labels are AI-assisted under fixed rules (Section 3.3), with no inter-annotator agreement; alignment decisions, especially for the 21 ambiguous claims, rest on one pass.
- **Small sample:** 102 claims, four outlets (two planned outlets refused the crawler), just over three months; PMUY (4) and MGNREGA (9) are thin. Results describe this sample, not all Hindi news.
- **Unbindable means not found in the listed central sources,** not false; search time was not logged, data.gov.in and state releases were not searched, and live dashboards overwrite past values. Binding checks consistency with official figures, not truth.
- **One verifier, one run:** one model, the closed-book condition only, one run at temperature 0, free tier, one day. The planned models were unavailable to new keys (HTTP 404) and gemini-3.8-flash was overloaded (HTTP 503), so no model comparison is possible; results may not transfer to larger, later or search-enabled models.
- **Knowledge cut-off:** the claims are from 2026 and half the abstentions say the article date is in the future, so the closed-book test is probably mainly about claims newer than the model's training data.
- **Language pair:** the English gloss was written by the AI agent and sometimes adds context from the surrounding sentence (Appendix B example), so the pair differs in wording as well as language.
- **Source checks** ran from one network on one day; two cited PM-JAY addresses did not load.

### Future Work

Run the gold-evidence and distractor conditions; test several models, including search-enabled ones, over several runs; add an independent second labeller; extend to more outlets and state schemes.

## 6. Conclusion

In 102 numerical claims about six central schemes in Hindi news, 45.1% could be bound to a dated official statistic and 24.5% cleanly, with national claims bound far more often (69.2%) than state claims (20.0%); cleanly bound claims matched 88.0% of the time. A free LLM verifier, asked without evidence, said "cannot verify" on 92.2% of answers, almost equally on claims with and without official evidence, and scored below an always-abstain baseline; its 16 committed answers were right 4 times, and no cited page showed the stated figure.

For people building fact-checking tools and AI research agents for Hindi readers, "cannot verify" will often be the correct answer for scheme numbers, especially at state level. A verifier should be judged on whether its abstentions follow the evidence and whether its sources hold up, not on how often it abstains.

## Code and Data

- **Code repository:** https://github.com/WST2002/saboot (scripts for every step, table and figure).
- **Data/Datasets:** same repository: the 102 claims (clause, headline, URL and metadata; no full articles), labels with evidence quotes, page-verification records, all 204 verifier answers and the URL checks.
- **Preexisting work:** none; all code, data and text were produced during the sprint (13 to 15 November 2026).

## References

1. Peter Røysland Aarnes, Vinay Setty. 2025. NumPert: Numerical Perturbations to Probe Language Models for Veracity Prediction. arXiv:2511.09971. https://arxiv.org/abs/2511.09971
2. Jacob Devasier, Akshith Putta, Qing Wang, Alankrit Moses, Chengkai Li. 2026. Frame-Guided Synthetic Claim Generation for Automatic Fact-Checking Using High-Volume Tabular Data. arXiv:2601.17232. https://arxiv.org/abs/2601.17232
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

**What the result establishes and what it does not.** The study establishes, for one sample of Hindi news on six central schemes, how often a numerical claim can be linked to a dated official figure in a fixed list of central sources, how often the two agree, and how one free LLM verifier behaves on these claims without evidence. It does not establish whether any outlet is accurate in general, whether the official figures are true, whether any journalist or official intended to mislead, or how other models or later versions behave. A mismatch is a measurement outcome under stated rules and may come from a date lag, a definition difference or rounding. An "unbindable" label means we did not find public evidence in the listed sources, not that the claim is false.

**How the dataset or a binding tool could be misused.** *Selective attacks on outlets:* a list of mismatches could be cherry-picked to discredit one newspaper or one government; we publish aggregate rates and every claim with its evidence, including all the matches, and describe mismatches as measurement outcomes, not accusations. *Treating official numbers as truth:* a "match" label could be presented as proof that a claim is true; binding checks consistency with official figures, not ground truth. *Gaming:* publishers could phrase claims vaguely ("करोड़ों लोगों को लाभ") so they stay unbindable; a vague-claim rate, not measured here, would make such a shift visible. *Over-trust in AI verifiers:* our results show a verifier citing official-looking sources that do not show the figure; neither the dataset nor any tool built on it should be presented as an automatic truth checker. *Political neutrality:* schemes were chosen by news coverage volume, not by party, and every claim is tagged by speaker.

**Personal data and source handling.** We collected news articles and aggregate scheme statistics only; no personal data was collected. Several scheme portals expose beneficiary-level lists; these were never opened, scraped or stored. Crawling was polite (a 3-second delay between requests, robots.txt respected). Outlets that disallowed or refused the crawler were excluded. Raw pages were cached locally only to confirm that each claim clause and evidence quote appears verbatim; the release contains only the URL, date, headline and claim clause, not full articles. The verifier used a free API key; no personal data was sent to the model.

## Appendix B: Verifier Prompt (as used)

The exact prompt sent for each call (scripts/run_verifier.py). {scheme} is the scheme's full name, {claim} the verbatim Hindi clause or its English gloss, and {date} the article date. The request set temperature 0 and a JSON response type.

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

TABLE: **Table C.3.** The three strict mismatches, largest gap first. Official values with the as-of date of the official figure; all three official figures are from PIB.
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

TABLE: **Table C.5.** The seven PIB release IDs cited by the verifier (all 7 PIB citations; 7 distinct IDs). Each number exists, but the release it opens is unrelated to the claim. Actual titles were fetched from pib.gov.in on 14 November 2026 and are given in English translation.
| Claim | Source title given by the model | Release actually at that ID |
|---|---|---|
| C002 (hi) | PM-KISAN: Over Rs 3.42 lakh crore transferred to more than 11 crore farmers ... | Weekly Holi special train between Lokmanya Tilak Terminus and Prayagraj (Hindi) |
| C029 (en) | Cabinet Decisions on Pradhan Mantri Awas Yojana | Shri Pralhad Joshi takes charge of the Ministry of New and Renewable Energy (Punjabi) |
| C043 (en) | Ayushman Bharat PM-JAY crosses 6 crore hospital admissions | English rendering of the Prime Minister's speech to the Indian community in Warsaw, Poland (Kannada) |
| C057 (en) | Cabinet Committee on Economic Affairs approval for continuation of PMUY | Indian Sign Language centre to celebrate Sign Language Day on 23 September 2023 (Hindi) |
| C081 (hi) | Ayushman Bharat PM-JAY Official Website / PIB | PM GatiShakti network planning group evaluates infrastructure projects (Manipuri) |
| C081 (en) | Ayushman Bharat PM-JAY reaches a major milestone of 6 crore hospital admissions | Complementary feeding for healthy child growth, a theme of Poshan Maah 2024 (Malayalam) |
| C092 (en) | Press Information Bureau Release on PM-KISAN | Prime Minister greets on the Sikh New Year (Hindi) |

TABLE: **Table C.6.** Calibration of all 204 answers (both languages) by stated confidence. Bins include the lower bound and exclude the upper one (the last bin includes 1.0). "Correct" means the verdict equals the expected verdict; ECE = sum over bins of (answers / 204) × |mean confidence − share correct| = 0.517.
| Stated confidence | Answers | Mean confidence | Verdict correct | Of which CANNOT_VERIFY |
|---|---|---|---|---|
| 0.00-0.50 | 85 | 0.00 | 77.6% (66/85, 67.7-85.2) | 85 |
| 0.50-0.80 | 1 | 0.50 | 100.0% (1/1, 20.7-100.0) | 1 |
| 0.80-0.90 | 4 | 0.80 | 100.0% (4/4, 51.0-100.0) | 3 |
| 0.90-0.95 | 4 | 0.90 | 75.0% (3/4, 30.1-95.4) | 2 |
| 0.95-1.00 | 110 | 0.995 | 65.5% (72/110, 56.2-73.7) | 97 |

Article and official URLs for every row of Tables C.3 and C.4 are in report/tables.md; every verifier answer and URL check is in report/verifier_tables.md.

## LLM Usage Statement

AI assistants were used throughout this project. An AI agent (Claude, by Anthropic, run in Claude Code on the author's laptop) collected and fetched the articles, chose the claim clauses, wrote the English glosses, searched the official sources, recorded each official figure with a verbatim quote, and drafted the labels and their rationales under the fixed rules in data/labelling-rules.md. Scripts applied the match rule, checked that every claim clause and evidence quote appears verbatim in the saved pages, scored the verifier answers, checked every cited URL, and computed every number in this report. The agent opened every official page behind a binding in the author's browser to check the figure, date and scope against the record. Gemini (gemini-3.5-flash-lite) was used only as the experimental subject of Section 4.3, after all labels were fixed; it did not help label, analyse or write. AI assistants also wrote the analysis scripts and drafted and edited the text of this report. There was no independent second human labeller. The author designed the study, set the rules, directed the work, and is responsible for all content.

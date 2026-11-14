# Saboot: related work and novelty (checked 2026-11-14)

Every entry below was opened on arXiv / ACL Anthology / the publisher page on 2026-11-14 unless marked "(known, standard reference)". Do not add a reference to the report unless it is in this file or has been opened the same way.

## Novelty verdict

No work found that binds **real Hindi news numerical claims** to **Indian official statistics** and measures (a) how much of a real domain is bindable and (b) whether LLM verifiers abstain vs invent sources. Closest neighbours and the gap:

| Work | What it does | Gap vs Saboot |
|---|---|---|
| Devasier et al. 2026 (OECD tables, includes Hindi) | **Closest.** Synthetic claims generated from OECD tables, in English, Chinese, Spanish and Hindi | Claims are **synthetic**, evidence is OECD, not Indian government data; no coverage measurement of a real news domain |
| IndicClaimBuster (2025) | ~9K claims from Indian news in English, Hindi, Bengali, code-mixed; evidence 2 LLM-generated + 1 manual | Not numerical-specific; evidence not official statistics; partly LLM-generated evidence |
| HiFACTMix (2025) | 1,500 Hinglish (code-mixed) political claims by 28 Chief Ministers, with evidence + labels | Code-mixed, not Hindi news; evidence not tied to official statistics; no numeric focus stated |
| QuanTemp (2024) | 15,514 real numerical/temporal claims from fact-checkers, English | English only; web-snippet evidence |
| CLEF-2026 CheckThat! Task 2 | Numerical and temporal claim verification | **Languages: English, Spanish, Arabic. No Hindi** (lab overview, arXiv 2602.09516 HTML: "(Languages: English, Spanish and Arabic.)"); English data reuses QuanTemp |
| ClaimDB (2026) | Claims verified over large real databases; notes models struggle to abstain | English, generic databases, not news→official statistics |
| NumPert (2025) | Numeric perturbations probing LLM veracity prediction | Probe of robustness, not binding coverage; not Hindi |
| PIB Fact Check unit | Government unit that labels viral claims (mostly fake schemes) as fake | Manual, debunks fabricated schemes; does not measure news-number agreement |
| REASONS (2024) | Benchmarks abstention vs hallucination for scientific citations | Same metric idea (abstain vs hallucinate) but scientific citations, English |

Also checked: IndicClaimVer shared task at FIRE 2026 (evidence selection + verification for English/Hindi/Bengali/code-mixed, built on IndicClaimBuster: https://sites.google.com/view/indicclaimver2026) — not numerical, not official statistics. Indian fact-checkers (BOOM, FactChecker.in) do manual checks of scheme numbers against official data, e.g. https://www.boomlive.in/9-modis-16-claims-govt-schemes-true-3-false — good motivation examples, not a dataset.

## Verified citations

1. Venktesh V, Abhijit Anand, Avishek Anand, Vinay Setty. 2024. *QuanTemp: A real-world open-domain benchmark for fact-checking numerical claims.* arXiv:2403.17169. https://arxiv.org/abs/2403.17169
2. Rakesh Thakur, Sneha Sharma, Gauri Chopra. 2025. *HiFACTMix: A Code-Mixed Benchmark and Graph-Aware Model for Evidence-Based Political Claim Verification in Hinglish.* arXiv:2508.10001. https://arxiv.org/abs/2508.10001
3. Pritam Pal, Shyamal Krishna Jana, Dipankar Das. 2025. *IndicClaimBuster: A Multilingual Claim Verification Dataset.* Proceedings of IJCNLP-AACL 2025, pp. 2478-2489. https://aclanthology.org/2025.ijcnlp-long.133/
4. Julia Maria Struß, Sebastian Schellhammer, Stefan Dietze, Venktesh V, Vinay Setty, Tanmoy Chakraborty, Preslav Nakov, Avishek Anand, Primakov Chungkham, Salim Hafid, Dhruv Sahnan, Konstantin Todorov. 2026. *The CLEF-2026 CheckThat! Lab: Advancing Multilingual Fact-Checking.* arXiv:2602.09516. https://arxiv.org/abs/2602.09516
5. Jacob Devasier, Akshith Putta, Qing Wang, Alankrit Moses, Chengkai Li. 2026. *Frame-Guided Synthetic Claim Generation for Automatic Fact-Checking Using High-Volume Tabular Data.* arXiv:2601.17232. https://arxiv.org/abs/2601.17232
6. Michael Theologitis, Preetam Prabhu Srikar Dammu, Chirag Shah, Dan Suciu. 2026. *ClaimDB: A Fact Verification Benchmark over Large Structured Data.* arXiv:2601.14698 (ACL 2026). https://arxiv.org/abs/2601.14698
7. Peter Røysland Aarnes, Vinay Setty. 2025. *NumPert: Numerical Perturbations to Probe Language Models for Veracity Prediction.* arXiv:2511.09971. https://arxiv.org/abs/2511.09971
8. Andreas Vlachos, Sebastian Riedel. 2015. *Identification and Verification of Simple Claims about Statistical Properties.* EMNLP 2015. https://eprints.whiterose.ac.uk/91378/ — early work checking statistical claims against a knowledge base (Freebase), with approximate numeric matching; motivates the tolerance rule.
9. Deepa Tilwani, Yash Saxena, Seyedali Mohammadi, Ankur Padia, Edward Raff, Amit Sheth, Srinivasan Parthasarathy, Manas Gaur. 2024. *Abstention vs. Hallucination: Benchmarking LLM Source Attribution for Scientific Citations* (REASONS). arXiv:2405.02228. https://arxiv.org/abs/2405.02228
10. Ashim Gupta, Vivek Srikumar. 2021. *X-FACT: A New Benchmark Dataset for Multilingual Fact Checking.* ACL 2021 (short). https://aclanthology.org/2021.acl-short.86/

Background (known, standard references; re-open before citing):
- James Thorne, Andreas Vlachos, Christos Christodoulopoulos, Arpit Mittal. 2018. *FEVER: a large-scale dataset for Fact Extraction and VERification.* NAACL 2018. https://arxiv.org/abs/1803.05355 — origin of the "NotEnoughInfo" label.
- Michael Schlichtkrull, Zhijiang Guo, Andreas Vlachos. 2023. *AVeriTeC: A Dataset for Real-world Claim Verification with Evidence from the Web.* NeurIPS 2023 Datasets and Benchmarks. https://arxiv.org/abs/2305.13117

Left out on purpose (could not confirm details): secondary summaries of "fact-ablated evaluation" and the Stanford FSI chatbot fact-checking study; the Poly-FEVER OpenReview submission (status unclear).

## How to position Saboot (one paragraph for the report)

Prior numeric fact-checking benchmarks are English-first (QuanTemp, CheckThat! 2026 Task 2 in English/Spanish/Arabic) or use synthetic claims over tables (Devasier et al. 2026, ClaimDB). Indian-language verification datasets (IndicClaimBuster, HiFACTMix) are not numerical and do not use official statistics as evidence. Saboot measures, on real Hindi news, how much numerical content is bindable to government statistics at all, how often it agrees, and whether free LLM verifiers abstain or fabricate sources when the evidence is missing: the Track 2 coverage question for one real domain.

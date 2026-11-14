# Saboot: data sources (checked 2026-11-14, ~10:00 IST)

"Reachable" = plain HTTP GET from this laptop returned the page with no login. "Numbers in HTML" = the figures are in the server response (scrapeable with requests + HTML parsing). "JS" = figures load by JavaScript and need a browser (Playwright) or the underlying XHR call.

## Key caveat for every dashboard

Scheme dashboards show **"as on today"** cumulative numbers. A news claim from 3 months ago cites an older value. To bind old claims you need a dated source: (a) a PIB release from the same week, (b) a Lok Sabha / Rajya Sabha answer with a date, or (c) a Wayback Machine snapshot of the dashboard near the article date (web.archive.org). Record the evidence date for every binding.

## Official sources by scheme

| Scheme | Official URL(s) | Reachable without login | Notes |
|---|---|---|---|
| PM-KISAN | https://pmkisan.gov.in/ | Yes | Homepage text names the latest instalment (24th, released 30 Oct 2026, Banaskantha). Beneficiary/amount totals are mostly in PIB releases, not the homepage. Note: TLS cert chain incomplete (some fetchers fail; curl worked). |
| PM Awas Yojana - Gramin | https://pmayg.dord.gov.in/ ; report: https://report.pmayg.dord.gov.in/netiay/homereports/HomeCumulativeDataReport.aspx?type=1 (type=1..4) | Yes | **Best source.** State-wise target table is in plain HTML, dated (RecordDate 14-11-2026), with XLS/PDF download buttons. |
| PM Awas Yojana - Urban | https://pmay-urban.gov.in/ ; progress PDFs linked from homepage, e.g. `uploads/progress-pdfs/...Achievement_under_PMAY-U_&_PMAY-U2.0...pdf`, `State_wise_for_web.pdf`, `City_wise_Progress_PMAY-U_090925.pdf` | Yes | Numbers are in dated PDFs (sanctioned / grounded / completed). |
| PM Ujjwala Yojana | https://pmuy.gov.in/index.aspx | Yes | **Numbers in HTML with a date:** "Total Connections Released under PMUY *as on 23 Sep 2026: 105,685,306"; "latest PMUY extension (25 lakh) as on 23 Sep 2026: 2,442,525". |
| Jal Jeevan Mission | https://ejalshakti.gov.in/jjmreport/JJMIndia.aspx | Yes, but JS | Page loads; the figures (total rural HHs, tap connections, % coverage) are filled by JavaScript (raw HTML shows 0). Use Playwright, or PIB/Parliament answers. |
| MGNREGA | https://nrega.dord.gov.in/ (nrega.nic.in redirects here); At a glance: https://mnregaweb4.dord.gov.in/netnrega/nrega_ataglance/At_a_glance.aspx ; MIS: https://mnregaweb4.dord.gov.in/netnrega/MISreport4.aspx | Yes | At-a-glance needs a state/year selection (ASP.NET postback). Financial-year totals (person-days, households worked, expenditure) are there. |
| Ayushman Bharat PM-JAY | https://pmjay.gov.in/ , https://nha.gov.in/ | pmjay.gov.in timed out from here; nha.gov.in returned a small JS shell | Treat as **blocker-prone**. Bind Ayushman claims to PIB releases and Parliament answers instead. |

## Cross-scheme sources (dated, citable)

| Source | URL | Status |
|---|---|---|
| PIB releases, Hindi | https://www.pib.gov.in/allRel.aspx?reg=3&lang=2 | **Confirmed Hindi.** Listing page is in Hindi; release pages are `https://www.pib.gov.in/PressReleasePage.aspx?PRID=<id>` (e.g. PRID=2336102, 14 Nov 2026, Hindi, contains figures like "4,172 वन धन विकास केंद्र", "12.48 लाख"). Hindi and English versions of the same release have **different PRIDs**; link them by date + ministry + title. |
| PIB releases, English | https://www.pib.gov.in/allRel.aspx?reg=3&lang=1 | Same structure. |
| PIB Fact Check | linked from the PIB menu ("तथ्यों की जांच") | Debunks fake schemes; not a numbers source. |
| Lok Sabha Q&A | https://sansad.in/ls/questions/questions-and-answers | Page loads (JS search). Answers are dated PDFs, often with Hindi versions. |
| Rajya Sabha Q&A | https://sansad.in/rs/questions/questions-and-answers | Same. |
| Open Government Data | https://www.data.gov.in/ | Site loads. **API needs a free API key (registration)**; many datasets are Parliament-answer tables. Optional; she must register herself. |

## Hindi news sources

| Source | Why | Crawl status |
|---|---|---|
| Amar Ujala | Heavy scheme coverage (tag pages e.g. https://www.amarujala.com/tags/pm-kisan-samman-nidhi) | robots.txt allows `User-agent: *`; news sitemap https://www.amarujala.com/sitemap-news-v1.xml; tag page fetched OK. |
| Dainik Jagran | Largest Hindi daily; topic pages e.g. https://www.jagran.com/topics/pm-kisan-samman-nidhi-yojana | Topic page fetched OK; sitemaps https://www.jagran.com/news-sitemap.xml |
| Navbharat Times | Times group Hindi; has English sister (Times of India / ET) for Hindi-English pairs | robots.txt allows; https://navbharattimes.indiatimes.com/news-sitemap.xml |
| BBC Hindi (optional) | Has an English parent (BBC News) for paired claims | https://www.bbc.com/hindi fetched OK |

Excluded: **Live Hindustan** (robots.txt `Disallow: /` for all agents), **Dainik Bhaskar** (robots.txt returns 403).

Only store: URL, date, headline, the claim sentence. Do not republish full articles (copyright).

## Top 5 for the study

1. PIB Hindi + English releases (dated, both languages, every scheme)
2. PMAY-G report pages (HTML tables, dated, XLS download)
3. PMUY homepage (dated totals in HTML)
4. Lok Sabha / Rajya Sabha answers (dated, authoritative, historical values)
5. Amar Ujala tag pages + news sitemap (claims side)

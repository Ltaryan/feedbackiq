# PRD: FeedbackIQ, customer feedback analyser for 10-minute food delivery

| | |
|---|---|
| **Status** | v1 and v1.1 built (portfolio prototype); v2 planned |
| **Owner** | Product Manager (author) |
| **Last updated** | October 2026 |
| **Type** | Internal tool for CX, Ops and Product teams |

> Independent portfolio project. Not affiliated with any delivery company. All bundled data is synthetic.

---

## 1. Problem

A 10-minute food delivery app makes a hard promise: hot food at the door within minutes. When that promise breaks, customers say so in app-store reviews, in-app ratings and support tickets.

Today, at a typical quick-commerce company:

- **Volume is too high to read.** Thousands of reviews a week; people read a sample.
- **Tagging is manual and inconsistent.** Different agents tag the same complaint differently.
- **Priorities are anecdotal.** The loudest or most recent complaint wins, not the most frequent or costly.
- **Insights lack proof.** Summaries reach leadership without quotes or counts, so they get debated rather than acted on.

**Problem statement:** CX and product teams cannot quickly and reliably see *which* customer problems are most frequent, *with evidence*, and *which to fix first*.

## 2. Goals and non-goals

### Goals (v1)
1. Turn a CSV of reviews into a mood and topic for every review in under a minute.
2. Rank pain points by counted negative reviews, each backed by verifiable quotes and review IDs.
3. Propose prioritised fixes, clearly labelled as hypotheses.
4. Measure label quality against human labels, and show it in the product.
5. Work with **no AI and no cost** by default; AI is an opt-in upgrade.

### Non-goals (v1)
- Replying to customers or handling individual tickets.
- Real-time streaming from app stores or support tools.
- Predicting revenue or churn impact.
- Multi-user login and permissions (needed before real company data; see section 11).

## 3. Users

| Persona | Job to be done | What they need from FeedbackIQ |
|---|---|---|
| **Priya, CX lead** | "Tell me what customers are angriest about this week so I can brief the ops team." | Ranked pain points with quotes; a shareable report |
| **Arjun, Product manager (app)** | "Is checkout breaking for people, and how often?" | Filter by topic; read the raw reviews; counts over time |
| **Meera, City ops manager** | "Are missing items a packing problem at our stores?" | Topic counts and examples to take to store partners |
| **Data / ML analyst** | "Can we trust these labels?" | Accuracy, confusion matrix, list of mistakes, method used per row |

## 4. User stories

| # | As a… | I want to… | So that… | v1 |
|---|---|---|---|---|
| U1 | CX lead | upload last week's reviews as a CSV | I don't need engineering help | ✅ |
| U2 | CX lead | see which rows were rejected and why | I trust the totals | ✅ |
| U3 | PM | see the top pain points with real quotes | I can convince others with evidence | ✅ |
| U4 | PM | see suggested fixes ranked by impact vs effort | I can plan the sprint | ✅ |
| U5 | Analyst | see accuracy against human labels | I know how far to trust the output | ✅ |
| U6 | Anyone | filter by mood, topic, rating, order type and date | I can focus on one area | ✅ |
| U7 | Anyone | download a CSV and a written report | I can share results | ✅ |
| U8 | Privacy officer | personal details hidden, and AI off unless chosen | customer data is protected | ✅ |
| U9 | Ops manager | an urgent alert for food-safety complaints | health risks are escalated the same day | v2 |
| U10 | CX lead | week-over-week trend alerts | I spot spikes early | v2 |

## 5. Solution overview

```
Upload CSV → Validate → Mask PII → Sentiment + themes (rules, or Claude with fallback)
          → Pain points → Recommendations → Quote verification → Dashboard, Evaluation, Export
```

**Key design decisions**

| Decision | Why | Trade-off |
|---|---|---|
| Rule-based method is the default | Free, instant, private, explainable | Lower accuracy (75%) and misses sarcasm |
| LLM is opt-in, with a per-row fallback | Better understanding without making the tool depend on an API | Costs money; data leaves the company |
| Sentiment uses text only, not star rating | Ratings are noisy (a 4-star review can complain); keeps rating as an independent check | Some easy signal is ignored |
| Quotes are extracted, never generated, then verified | Zero risk of invented evidence | Quotes are whole sentences, not tight summaries |
| Recommendations are labelled hypotheses with a heuristic score | Honest about uncertainty | Less "decisive" looking |
| Fixed, domain-specific theme list (8 + Other) | Consistent tagging that maps to team ownership | New issue types land in "Other" until added |
| PII masked at intake | One place to protect every downstream use | Names are not detected |

## 6. Functional requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| F1 | Accept a CSV with `feedback_text`; `review_id`, `date`, `rating` and `order_type` are optional | Common aliases accepted (`review`, `text`, `comment`, `id`); a clear error if the text column is missing |
| F2 | Validate and report | Empty text and duplicate IDs/texts excluded, with a reason per row; bad ratings/dates blanked and counted; mixed date formats read (day-first) |
| F3 | Mask PII | Phones, emails, UPI IDs and card numbers replaced before display, export or LLM |
| F4 | Sentiment per review | Positive / Neutral / Negative; method recorded per row |
| F5 | Themes per review | Zero or more of 8 themes; otherwise "Other / Unclassified" |
| F6 | Pain points | Ranked by negative count (ties: total mentions, then name); evidence level; up to 2 verified quotes; all negative review IDs |
| F7 | Recommendations | Top 5 pain points with ≥ 3 negatives; impact 1–5, effort 1–5, score = impact ÷ effort; priority High/Medium/Low |
| F8 | Quote audit | Every displayed quote must be an exact substring of its cited review, or an error is shown |
| F9 | Evaluation | Accuracy, confusion matrix, per-class precision/recall, misclassified list on a separate labelled set |
| F10 | Export | UTF-8 CSV (Excel-safe, formula-injection-safe) and a Markdown report |
| F11 | Dashboard filters | Sentiment, theme, order type, rating range, date range; insights stay on the full dataset |
| F12 | SQL analytics | `analytics/queries.sql` answers product questions over `reviews` + `review_themes` tables (complaint rate by order type, top theme per month, text vs star agreement, co-occurring complaints); results pinned by tests |

## 7. AI requirements

| Area | Requirement |
|---|---|
| Model | Anthropic Claude (`claude-opus-5-5`, default) or Google Gemini (`gemini-3.8-flash`, free tier), chosen by which key is set or `FIQ_PROVIDER` |
| Output | Structured JSON constrained by a schema; only allowed sentiments and themes accepted |
| Batching | 20 reviews per request |
| Failure handling | Any error, refusal, truncation or invalid label → that review uses the rules; a banner reports how many |
| Prompt injection | Review text sent as JSON data; labels for IDs outside the batch ignored |
| Cost guard | At most 500 reviews per run (`FIQ_MAX_LLM_REVIEWS`); the rest use rules, with a visible note |
| Privacy | Off by default; an explicit warning before sending; PII masked first |
| Transparency | Every row shows which method labelled it |
| Quality gate | Before AI mode is recommended for a team, its accuracy must be measured on the evaluation set and beat the rules |

## 8. Success metrics

v1 is a prototype; these are the **targets** for a pilot with a real team.

| Type | Metric | Target |
|---|---|---|
| **North star** | Time from "reviews exported" to "top 3 issues agreed with evidence" | From ~1 day (manual reading) to **< 30 minutes** |
| Quality | Negative-class recall (complaints caught) | ≥ 85% (rules 75%; Gemini 100% on the 20-review set) |
| Quality | Overall sentiment accuracy on a 200-review, double-labelled set | ≥ 85% with the LLM |
| Trust | Quote audit pass rate | **100%** (hard requirement) |
| Trust | Share of reviews in "Other / Unclassified" | < 10% |
| Adoption | Weekly active CX/product users in pilot | ≥ 5 |
| Outcome | Recommendations taken into a sprint or ops action per month | ≥ 2 |
| Guardrail | PII found in exports or LLM payloads | 0 |
| Guardrail | LLM cost per 1,000 reviews | Tracked and within budget |

**Current measured results (synthetic data, 20-review evaluation set):**

| Method | Accuracy | Positive P/R | Neutral P/R | Negative P/R |
|---|---|---|---|---|
| Rule-based | 15/20 = 75% | 70% / 100% | 67% / 40% | 86% / 75% |
| Gemini `gemini-3.8-flash` | 20/20 = 100% (3 of 3 runs) | 100% / 100% | 100% / 100% | 100% / 100% |

Quote audit: 100%. Gemini also labelled the mood of all 11 known-gap sentences correctly, but put food-safety, rider and payment complaints under existing, wrong topics. **Decision:** the evaluation set is too small and too easy to tell good LLMs apart, so v2 grows it to 200+ real, double-labelled reviews, and the missing topics are added as a product change, not left to the model.

## 9. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Food-safety complaints missed | **High:** health/legal | v2: dedicated theme + urgent alert (P0) |
| Wrong labels drive wrong priorities | Medium | Visible accuracy, mistakes list, method per row, evidence levels |
| Made-up quotes or numbers | High (trust) | Quotes extracted and verified; counts computed from data |
| Customer PII leaves the company | High | Masking at intake; LLM off by default; no `.env` in git |
| LLM cost spikes on large uploads | Medium | 500-review cap per run |
| Prompt injection through review text | Medium | JSON data framing; label whitelist; per-batch ID check |
| Small/synthetic evaluation set over-states quality | Medium | Grow to 200+ real reviews with two labellers |
| Spreadsheet formula injection in exports | Medium | Cells starting with `= + - @` are escaped |

## 10. Release plan

| Phase | Scope | Exit criteria |
|---|---|---|
| **v1 (done)** | Everything in sections 6–7; synthetic data; 137 automated tests | Rules 75% on the eval set; quote audit 100%; all tests pass |
| **v1.1 (done, except demo)** | LLM evaluation measured (Gemini 100% vs rules 75%); Gemini free-tier support; live demo on Streamlit Cloud (pending) | LLM accuracy recorded and compared with rules ✅ |
| **v2** | Food safety, Delivery partner and Payments themes; food-safety alert; trend alerts; 200-review double-labelled eval set | Negative recall ≥ 85%; "Other" < 10% |
| **v3** | Store/city breakdowns; refund-cost link; label-correction feedback loop; Hindi/Hinglish; login | Pilot team uses it weekly |

## 11. Open questions

1. Which data sources should come first in a real pilot: app-store reviews, in-app ratings or support tickets?
2. Who owns each theme (for routing): Ops, Product or Restaurant partnerships?
3. What is the acceptable cost per 1,000 reviews for AI mode?
4. Is sending masked review text to an external AI provider approved by legal and security, or is a self-hosted model required?
5. Should food-safety alerts go to a person (on-call) or a ticket queue?

## 12. Appendix: v1 results on the synthetic sample

| Rank | Pain point | Negative / mentions | Evidence |
|---|---|---|---|
| 1 | Missing or incorrect items | 8 / 10 | Strong |
| 2 | App experience & checkout | 6 / 11 | Strong |
| 3 | Food quality & temperature | 6 / 11 | Strong |
| 4 | Refunds & customer support | 5 / 7 | Moderate |
| 5 | Pricing, fees & offers | 4 / 8 | Moderate |

Top recommendation: packing checklist with a handover photo and a two-tap "missing item" report (impact 5, effort 2, score 2.5, High priority).

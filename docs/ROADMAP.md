# FeedbackIQ roadmap: next 3 months

| | |
|---|---|
| **Horizon** | November 2026 – January 2027 |
| **Format** | Now / Next / Later (commitment drops as the horizon grows) |
| **Owner** | Product (author) |
| **Inputs** | PRD success metrics, evaluation results, SQL analysis, known-gap tests, Mixpanel usage events |

## Goal for the quarter

**Make FeedbackIQ trustworthy enough for a CX team to use weekly**: no missed safety complaints, labels measured on real data, and usage we can see.

## How items were prioritised

Each item was scored on **evidence** (what we measured), **risk if not done**, and **effort**. Items backed by a measured gap, or protecting users from harm, go first.

| Evidence we have | What it points to |
|---|---|
| 12 known gaps in the rules: 9 mood, 3 topic. The LLM fixed 9/9 mood gaps but **0/3 topic gaps** | Missing topics are a product decision, not a model problem |
| LLM 100% vs rules 75%, but on **20 synthetic, self-labelled reviews** | The test set can no longer tell good models apart |
| SQL: meal orders **~3×** the complaint rate of snacks; missing items **#1 every month** | Steady, process-level problems worth an experiment |
| No usage data until analytics was added | We can't yet say which features people use |

---

## NOW: Month 1 (committed)

| Item | Why now | Success measure | Effort |
|---|---|---|---|
| **Food safety & hygiene topic + same-day alert** | P0. "Found a hair in my biryani" is filed under *Food quality*; a missed safety complaint is a health, legal and brand risk, so the cost of a miss is far higher than any other error | 100% of food-safety test cases routed to the alert; alert reaches a named owner the same day | M |
| **Delivery-partner and Payments topics** | The other 2 topic gaps; the LLM files rude-rider and cash-change complaints under *Pricing* | All 3 topic-gap tests pass in both modes; "Other" stays under 10% | S |
| **Evaluation set v2: 200 real reviews, two independent labellers** | 100% on 20 easy reviews is directional only; we need a held-out set to choose between models | Labeller agreement measured; LLM and rules re-scored; negative recall reported | M |
| **Analytics live (Mixpanel)** | Can't prioritise features without usage data | Funnel visible: session → analysis → evaluation → export | ✅ Done |

## NEXT: Month 2 (planned, may change)

| Item | Why | Success measure | Effort |
|---|---|---|---|
| **Complaint rate per 1,000 orders** | Raw counts rise with order volume; a rate shows whether things are really getting worse | Rate shown per theme and per week | M (needs order counts) |
| **Week-over-week trend alerts** | Catch spikes early ("missing items up 40% this week") | Alert fires on a seeded spike in testing; false alarms under 1 per week | M |
| **Store / city / order-type breakdowns** | SQL showed meal orders are ~3× worse; ops needs to know *where* | Breakdown available in the dashboard and export | S |
| **Packing-photo experiment** (with an ops partner) | The #1 recommendation needs proof before rollout | Run per [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md) | L (ops-dependent) |

## LATER: Month 3+ (direction, not commitment)

| Item | Why | Depends on |
|---|---|---|
| "Correct this label" feedback loop | Team corrections improve the system and grow the evaluation set | Evaluation set v2 |
| Hindi / Hinglish support | Common in Indian reviews; the rules ignore Hindi script | v2 evaluation numbers for Hindi |
| Login and access control | Required before real company data | A pilot team |
| LLM result caching and cost tracking | Don't pay twice for the same review; track cost per 1,000 reviews | Usage data |

## Not doing this quarter

- **Automatic replies to customers:** a different problem; needs trusted labels first.
- **Real-time streaming from app stores:** CSV upload is enough for a weekly review.
- **Revenue or churn prediction:** needs order and customer data we don't have.

## What would change this plan

- Evaluation v2 shows the LLM is much worse on real data → pause new features and fix quality first.
- Mixpanel shows nobody uses the Evaluation tab → simplify it and move the effort elsewhere.
- User interviews (see [USER_RESEARCH.md](USER_RESEARCH.md)) show CX leads need something else first → re-rank NEXT.

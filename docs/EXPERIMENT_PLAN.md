# Experiment plan: packing checklist + handover photo

> **Status: designed, not run.** FeedbackIQ is a portfolio project with no live orders. This plan shows how the #1 recommendation would be tested before a full rollout. All inputs marked *assumption* must be replaced with real data before launch.

## 1. Why this experiment

FeedbackIQ's analysis ranks **Missing or incorrect items** as the #1 pain point: 8 of 10 reviews about it are negative, and SQL shows it is the top complaint (or tied) **every month**, which points to a steady process problem, not a bad week. The recommended fix scores highest on impact ÷ effort (5 ÷ 2 = 2.5):

> Add a packing checklist with a photo of the sealed order at handover.

It is still a **hypothesis**: it costs store time on every order, so it should be proven before rolling out to every store.

## 2. Hypothesis

**If** store staff complete a short packing checklist and photograph the sealed order at handover, **then** the share of orders with a missing or incorrect item will fall by at least 20%, **because** most errors happen at packing and a checklist plus photo makes them visible before the rider leaves.

## 3. Design

| Decision | Choice | Why |
|---|---|---|
| **Unit of randomisation** | **Store** | The checklist changes how a whole store packs; randomising individual orders would mix both processes in one kitchen (contamination) |
| **Groups** | Control: current process. Treatment: checklist + handover photo | One change at a time, so the result is attributable |
| **Assignment** | Random, stratified by city and store order volume | Keeps the two groups comparable |
| **Duration** | 4 full weeks, after a 1-week training period that is excluded | Covers weekday/weekend cycles; excludes the learning dip |
| **Analysis** | Difference in missing-item rate, with store-clustered standard errors | Orders from the same store are correlated |

## 4. Metrics

| Type | Metric | Definition |
|---|---|---|
| **Primary** | Missing/incorrect-item rate | Orders with a confirmed missing or wrong item ÷ delivered orders |
| Secondary | Missing-item refunds per 1,000 orders | Refund cost is the business impact |
| Secondary | Missing-items share of negative reviews | The FeedbackIQ signal this experiment came from |
| **Guardrail** | Kitchen-to-handover time (median, p90) | The checklist must not break the 10-minute promise |
| **Guardrail** | Late-delivery rate | Same reason |
| Guardrail | Photo compliance | Under 80% means the process failed, not the idea |

## 5. Sample size

Two-sided test, α = 0.05, power = 80%.

| Input | Value | Source |
|---|---|---|
| Baseline missing-item rate | 2.0% of orders | *assumption*: replace with real data |
| Minimum detectable effect | −20% relative (2.0% → 1.6%) | Smallest drop worth the extra packing time |
| Orders per store in 4 weeks | 2,000 | *assumption* |
| Intra-store correlation (ICC) | 0.002 | *assumption*, conservative |

| Step | Result |
|---|---|
| If orders could be randomised individually | 17,339 orders per group |
| Design effect for store randomisation: 1 + (2,000 − 1) × 0.002 | ≈ 5.0 |
| Orders needed per group | ≈ 86,700 |
| **Stores needed** | **44 per group, 88 in total, for 4 weeks** |

Sensitivity: with ICC 0.001 it falls to 26 stores per group; detecting a larger −30% effect needs 19 stores per group (ICC 0.002).

The calculation uses the standard two-proportion formula, n = (z₀.₉₇₅ + z₀.₈)² × [p₁(1−p₁) + p₂(1−p₂)] ÷ (p₁ − p₂)², multiplied by the design effect.

## 6. Decision rule (agreed before launch)

| Result | Decision |
|---|---|
| Primary metric falls ≥ 20%, statistically significant, guardrails within limits | **Roll out** to all stores in phases |
| Primary falls, but handover time p90 rises > 60 s | **Iterate**: shorten the checklist, re-test |
| No significant change | **Stop**; investigate where errors really happen (order entry? restaurant?) |
| Photo compliance < 80% | Result invalid: fix the process and re-run |

## 7. Risks

- **Novelty effect:** staff are careful in week 1 only. Mitigation: exclude the training week, check the trend by week.
- **Reporting bias:** a new reporting button would raise *reported* missing items. Mitigation: no reporting change during the test.
- **Store mix:** a few large stores dominate. Mitigation: stratify by volume and report per-store results.

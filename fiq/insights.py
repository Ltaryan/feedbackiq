"""Pain points and recommendations built only from counted data.

Rules that keep insights honest:
  * every number is counted from the analysed table;
  * every quote is an exact sentence cut from the review it cites (verify_all_quotes checks this);
  * recommendations are labelled hypotheses, with impact/effort as heuristic estimates, not predictions.
"""

from __future__ import annotations

import re

import pandas as pd

from .constants import OTHER
from .themes import PATTERNS

MAX_QUOTES = 2
_SENTENCE = re.compile(r"[^.!?]+[.!?]*")

# Template advice per theme: (proposed improvement, expected benefit, assumptions, effort estimate 1-5)
PLAYBOOK = {
    "Delivery speed & ETA accuracy": (
        "Recalibrate the ETA model with recent actual delivery times and show a range instead of a single number "
        "when the kitchen or rider is delayed.",
        "Fewer complaints about broken time promises, because expectations match reality more often.",
        ["Late deliveries are partly an ETA-accuracy problem, not only a capacity problem",
         "Delivery-time data is available per order"],
        4,
    ),
    "Food quality & temperature": (
        "Track 'cold or soggy on arrival' reports per restaurant and work with the worst outlets on prep timing "
        "and insulated packaging.",
        "Fewer quality complaints concentrated at a small set of restaurants.",
        ["Complaints cluster at specific restaurants", "Restaurants will act on feedback"],
        3,
    ),
    "Missing or incorrect items": (
        "Add a packing checklist with a photo of the sealed order at handover, and let customers report a missing "
        "item from the order screen in two taps.",
        "Fewer missing-item incidents and faster resolution when they happen.",
        ["Most errors happen at packing, not at order entry", "Restaurants can add a photo step without delays"],
        2,
    ),
    "Pricing, fees & offers": (
        "Show the full price, including delivery and small-order fees, before checkout, and explain any surge fee "
        "in one line.",
        "Fewer complaints about surprise charges; better trust at checkout.",
        ["Complaints are about transparency more than the absolute price level"],
        2,
    ),
    "Restaurant & menu availability": (
        "Sync menu stock in real time and hide sold-out items, instead of cancelling after the order is placed.",
        "Fewer cancelled orders and less frustration from unavailable items.",
        ["Restaurants can update stock status", "Cancellations are mostly caused by stock-outs"],
        3,
    ),
    "App experience & checkout": (
        "Prioritise fixing crashes and freezes in the checkout flow, and add crash reporting to the payment and "
        "cart screens.",
        "Fewer abandoned orders and app-related complaints.",
        ["The reported problems are reproducible bugs, not network issues on the customer side"],
        3,
    ),
    "Refunds & customer support": (
        "Set a response-time target for support tickets and auto-approve small refunds for verified "
        "missing-item reports.",
        "Faster resolutions and fewer complaints about being ignored.",
        ["Most refund requests are small and low-risk", "Support capacity can meet a response-time target"],
        2,
    ),
    "Packaging & order condition": (
        "Introduce sealed, spill-proof containers for liquid dishes and a tamper seal for every bag.",
        "Fewer spilled or damaged orders.",
        ["Spills come from container type, not rider handling alone"],
        2,
    ),
}


def evidence_level(negative: int) -> str:
    if negative >= 6:
        return f"Strong ({negative} negative reviews)"
    if negative >= 3:
        return f"Moderate ({negative} negative reviews)"
    return f"Limited ({negative} negative reviews; treat as a signal, not a pattern)"


def extract_quote(text: str, theme: str) -> str:
    """The first sentence of `text` that matches the theme; otherwise the first sentence.
    The result is always an exact substring of `text`."""
    sentences = [m.group(0).strip() for m in _SENTENCE.finditer(text) if m.group(0).strip()]
    if not sentences:
        return text.strip()
    for s in sentences:
        if any(p.search(s) for p in PATTERNS.get(theme, [])):
            return s
    return sentences[0]


def _pick_quotes(neg: pd.DataFrame, theme: str) -> list[dict]:
    """Prefer reviews that match the theme most clearly, then the lowest rating, then the ID (deterministic)."""
    ranked = neg.assign(
        _hits=neg["feedback_text"].apply(lambda t: sum(1 for p in PATTERNS.get(theme, []) if p.search(t))),
        _rating=neg["rating"].fillna(6),
    ).sort_values(["_hits", "_rating", "review_id"], ascending=[False, True, True])
    return [{"review_id": r["review_id"], "quote": extract_quote(r["feedback_text"], theme)}
            for _, r in ranked.head(MAX_QUOTES).iterrows()]


def build_pain_points(df: pd.DataFrame, min_negative: int = 2) -> list[dict]:
    """Themes ranked by number of negative reviews (ties: more mentions first, then name)."""
    n = len(df)
    if n == 0:
        return []
    ex = df.explode("theme_list").reset_index(drop=True)
    ex = ex[ex["theme_list"] != OTHER]
    points = []
    for theme, grp in ex.groupby("theme_list"):
        neg = grp[grp["sentiment"] == "Negative"]
        if len(neg) < min_negative:
            continue
        total = len(grp)
        points.append({
            "theme": theme,
            "negative": len(neg),
            "total": total,
            "negative_share_of_theme": len(neg) / total,
            "negative_share_of_all": len(neg) / n,
            "summary": (f"{len(neg)} of the {total} reviews that mention this theme are negative "
                        f"({len(neg) / n:.0%} of all {n} analysed reviews)."),
            "evidence": evidence_level(len(neg)),
            "quotes": _pick_quotes(neg, theme),
            "review_ids": sorted(neg["review_id"].astype(str)),
        })
    points.sort(key=lambda p: (-p["negative"], -p["total"], p["theme"]))
    return points


def impact_estimate(negative: int, n_reviews: int) -> int:
    """1-5 from the share of ALL reviews that are negative about the theme."""
    share = negative / n_reviews if n_reviews else 0
    for cut, score in ((0.12, 5), (0.09, 4), (0.06, 3), (0.03, 2)):
        if share >= cut:
            return score
    return 1


def build_recommendations(points: list[dict], n_reviews: int, top: int = 5, min_negative: int = 3) -> list[dict]:
    """One recommendation per top pain point with enough evidence, ordered by score = impact / effort."""
    recs = []
    for p in points[:top]:
        if p["negative"] < min_negative or p["theme"] not in PLAYBOOK:
            continue
        text, benefit, assumptions, effort = PLAYBOOK[p["theme"]]
        impact = impact_estimate(p["negative"], n_reviews)
        score = round(impact / effort, 2)
        recs.append({
            "theme": p["theme"],
            "recommendation": text,
            "rationale": (f"{p['negative']} of {n_reviews} analysed reviews are negative about this theme "
                          f"({p['negative']} of the {p['total']} that mention it)."),
            "expected_benefit": benefit + " This is a hypothesis to test, not a measured result.",
            "assumptions": list(assumptions),
            "impact_estimate": impact,
            "effort_estimate": effort,
            "score": score,
            "priority": "High" if score >= 1.5 else "Medium" if score >= 1.0 else "Low",
            "score_note": (f"Impact {impact}/5 comes from the share of all reviews that are negative about this theme; "
                           f"effort {effort}/5 is a rough template estimate. Score = impact / effort."),
            "quotes": [dict(q) for q in p["quotes"]],
            "review_ids": list(p["review_ids"]),
            "text_source": "Rule-based template",
        })
    recs.sort(key=lambda r: (-r["score"], -r["impact_estimate"], r["theme"]))
    return recs


def verify_all_quotes(items: list[dict], df: pd.DataFrame) -> list[str]:
    """Return a list of problems; an empty list means every quote is an exact substring of the review it cites."""
    texts = dict(zip(df["review_id"].astype(str), df["feedback_text"].astype(str)))
    problems = []
    for item in items:
        for q in item.get("quotes", []):
            rid = str(q["review_id"])
            if rid not in texts:
                problems.append(f"{item['theme']}: quote cites unknown review {rid}")
            elif not q["quote"] or q["quote"] not in texts[rid]:
                problems.append(f"{item['theme']}: quote not found in review {rid}")
    return problems

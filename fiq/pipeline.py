"""Analysis pipeline: add sentiment and themes to every validated review, and record which method was used."""

from __future__ import annotations

import pandas as pd

from .constants import METHOD_RULES, OTHER
from . import llm
from .llm import classify_reviews
from .sentiment import rule_based_sentiment
from .themes import assign_themes


def analyze_dataframe(clean: pd.DataFrame, client=None):
    """Return (df, info).

    df gets: sentiment, theme_list (list), themes (text, '; '-joined) and analysis_method per row.
    With client=None every row uses the rule-based fallback. With a client, rows the LLM could not label
    fall back to rules, and info['warnings'] says how many.
    """
    df = clean.copy().reset_index(drop=True)
    warnings: list[str] = []
    labels: dict[str, dict] = {}
    method_llm = llm.method_label(client)
    if client is not None and len(df):
        rows = list(zip(df["review_id"].astype(str), df["feedback_text"].astype(str)))
        if len(rows) > llm.MAX_LLM_REVIEWS:
            warnings.append(f"Only the first {llm.MAX_LLM_REVIEWS} of {len(rows)} reviews were sent to the LLM "
                            "(cost limit, set FIQ_MAX_LLM_REVIEWS to change it); the rest used the rule-based fallback.")
            rows = rows[:llm.MAX_LLM_REVIEWS]
        labels, warn = classify_reviews(client, rows)
        if warn:
            warnings.append(warn)

    sentiments, themes, methods = [], [], []
    for rid, text in zip(df["review_id"].astype(str), df["feedback_text"].astype(str)):
        lab = labels.get(rid)
        if lab is not None:
            sentiments.append(lab["sentiment"])
            themes.append(lab["themes"] or [OTHER])
            methods.append(method_llm)
        else:
            sentiments.append(rule_based_sentiment(text))
            themes.append(assign_themes(text))
            methods.append(METHOD_RULES)

    df["sentiment"] = sentiments
    df["theme_list"] = themes
    df["themes"] = ["; ".join(t) for t in themes]
    df["analysis_method"] = methods

    llm_n = sum(m == method_llm for m in methods)
    if llm_n == 0:
        label = METHOD_RULES
    elif llm_n == len(df):
        label = method_llm
    else:
        label = f"{method_llm} for {llm_n} reviews, {METHOD_RULES} for {len(df) - llm_n}"
    info = {
        "method_label": label,
        "llm_reviews": llm_n,
        "rule_reviews": len(df) - llm_n,
        "warnings": warnings,
    }
    return df, info

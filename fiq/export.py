"""Downloads: the analysed table as CSV and a Markdown insights report."""

from __future__ import annotations

from datetime import date

import pandas as pd

from .constants import SENTIMENTS

CSV_COLUMNS = ["review_id", "date", "rating", "order_type", "feedback_text", "sentiment", "themes", "analysis_method",
               "source_row"]


FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _defuse_formula(value):
    """Spreadsheets run cells that start with = + - @ as formulas (CSV injection). Prefix them with '."""
    if isinstance(value, str) and value.startswith(FORMULA_START):
        return "'" + value
    return value


def analysed_csv_bytes(df: pd.DataFrame) -> bytes:
    """CSV of the analysed reviews (themes as one '; '-joined column). UTF-8 with BOM so Excel opens it cleanly."""
    out = df.copy()
    if "themes" not in out.columns and "theme_list" in out.columns:
        out["themes"] = out["theme_list"].apply("; ".join)
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    cols = [c for c in CSV_COLUMNS if c in out.columns]
    out = out[cols]
    for c in ("review_id", "feedback_text", "order_type"):
        if c in out.columns:
            out[c] = out[c].map(_defuse_formula)
    return out.to_csv(index=False).encode("utf-8-sig")


def _md_escape(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def report_markdown(df, points, recs, info, sample: bool, evaluation=None) -> str:
    n = len(df)
    counts = df["sentiment"].value_counts().reindex(SENTIMENTS, fill_value=0)
    lines = [
        "# FeedbackIQ insights report",
        "",
        f"Generated {date.today().isoformat()}. Method: **{info['method_label']}**.",
        "",
    ]
    if sample:
        lines += ["> Synthetic data: these reviews were written for a portfolio demo and are not real customer feedback.", ""]
    lines += ["## Overview", "", f"- Reviews analysed: {n}"]
    if df["rating"].notna().any():
        lines.append(f"- Average rating: {df['rating'].mean():.2f}")
    for s in SENTIMENTS:
        lines.append(f"- {s}: {counts[s]} ({counts[s] / n:.0%})" if n else f"- {s}: 0")
    for w in info.get("warnings", []):
        lines.append(f"- Note: {w}")

    lines += ["", "## Top pain points", ""]
    if not points:
        lines.append("No negative reviews with a theme were found.")
    for i, p in enumerate(points, 1):
        lines += [f"### {i}. {p['theme']}", "", p["summary"], "", f"Evidence level: {p['evidence']}", ""]
        lines += [f"> \"{q['quote']}\" ({q['review_id']})" for q in p["quotes"]]
        lines += ["", f"Negative review IDs: {', '.join(p['review_ids'])}", ""]

    lines += ["## Recommendations (hypotheses)", "",
              "Impact and effort are heuristic estimates, not measured or predicted outcomes.", ""]
    if not recs:
        lines.append("Not enough evidence for a recommendation.")
    else:
        lines += ["| # | Theme | Priority | Impact | Effort | Score |", "|---|---|---|---|---|---|"]
        lines += [f"| {i} | {_md_escape(r['theme'])} | {r['priority']} | {r['impact_estimate']} | {r['effort_estimate']} | {r['score']} |"
                  for i, r in enumerate(recs, 1)]
        lines.append("")
        for i, r in enumerate(recs, 1):
            lines += [f"### {i}. {r['theme']}", "",
                      f"- **Proposed improvement:** {r['recommendation']}",
                      f"- **Rationale:** {r['rationale']}",
                      f"- **Expected benefit (hypothesis):** {r['expected_benefit']}",
                      f"- **Assumptions:** {'; '.join(r['assumptions'])}",
                      f"- **Text source:** {r['text_source']}", ""]

    lines += ["## Evaluation", ""]
    if evaluation is None:
        lines.append("Not run for this report.")
    else:
        lines += [f"Method evaluated: {evaluation['method_label']}. "
                  f"Sentiment accuracy: {evaluation['correct']}/{evaluation['n']} = {evaluation['accuracy']:.0%}.", "",
                  "| Manual \\ Predicted | " + " | ".join(SENTIMENTS) + " |",
                  "|---|" + "---|" * len(SENTIMENTS)]
        conf = evaluation["confusion"]
        lines += [f"| {s} | " + " | ".join(str(int(conf.loc[s, c])) for c in SENTIMENTS) + " |" for s in SENTIMENTS]
        lines += ["", "Small synthetic set labelled by the project author: a demonstration, not a benchmark."]

    lines += ["", "---", "Independent portfolio project. Not affiliated with any delivery company.", ""]
    return "\n".join(lines)

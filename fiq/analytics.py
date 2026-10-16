"""SQL analytics over the analysed reviews (SQLite, in memory; no extra install).

Run:  python -m fiq.analytics            rule-based labels (repeatable)
      python -m fiq.analytics --llm      LLM labels (needs a key in .env)
The questions live in analytics/queries.sql so they can be read and reused on their own.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "analytics" / "queries.sql"
_HEADER = re.compile(r"^--\s*name:\s*(\S+)\s*$", re.M)
_QUESTION = re.compile(r"^--\s*question:\s*(.+)$", re.M)


def load_queries(path: Path = QUERIES) -> dict[str, dict]:
    """{name: {"question": str, "sql": str}} in file order."""
    text = path.read_text(encoding="utf-8")
    heads = list(_HEADER.finditer(text))
    out = {}
    for i, h in enumerate(heads):
        body = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        q = _QUESTION.search(body)
        out[h.group(1)] = {"question": q.group(1).strip() if q else "", "sql": body.strip()}
    return out


def build_database(df: pd.DataFrame) -> sqlite3.Connection:
    """Load an analysed table (output of analyze_dataframe) into SQLite as reviews + review_themes."""
    reviews = pd.DataFrame({
        "review_id": df["review_id"].astype(str),
        "date": pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d"),
        "rating": df["rating"],
        "order_type": df["order_type"].astype(str),
        "sentiment": df["sentiment"],
        "analysis_method": df["analysis_method"],
        "feedback_text": df["feedback_text"],
    })
    themes = (df[["review_id", "theme_list"]].explode("theme_list")
              .rename(columns={"theme_list": "theme"}).astype({"review_id": str}))
    con = sqlite3.connect(":memory:")
    reviews.to_sql("reviews", con, index=False)
    themes.to_sql("review_themes", con, index=False)
    return con


def run_all(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    con = build_database(df)
    try:
        return {name: pd.read_sql(q["sql"], con) for name, q in load_queries().items()}
    finally:
        con.close()


def main() -> None:
    import sys

    from .pipeline import analyze_dataframe
    from .validation import validate_reviews

    client = None
    if "--llm" in sys.argv:
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass
        from .llm import get_llm_client

        client, msg = get_llm_client()
        if client is None:
            sys.exit(f"Cannot use the LLM: {msg}")

    clean, _ = validate_reviews(pd.read_csv(ROOT / "sample_data" / "synthetic_reviews_60.csv"))
    df, info = analyze_dataframe(clean, client=client)
    print(f"Labels: {info['method_label']} ({len(df)} synthetic reviews)\n")
    queries = load_queries()
    for name, result in run_all(df).items():
        print(f"== {name}: {queries[name]['question']}")
        print(result.to_string(index=False) if len(result) else "(no rows)")
        print()


if __name__ == "__main__":
    main()

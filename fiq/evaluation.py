"""Sentiment evaluation against a small hand-labelled set (sample_data/eval_set_20.csv).

Run:  python -m fiq.evaluation
"""

from __future__ import annotations

import pandas as pd

from .constants import SENTIMENTS
from .pipeline import analyze_dataframe


def evaluate(eval_df: pd.DataFrame, client=None) -> dict:
    """Compare predicted sentiment with `manual_sentiment`. Needs feedback_text and manual_sentiment columns."""
    df = eval_df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = {"feedback_text", "manual_sentiment"} - set(df.columns)
    if missing:
        raise ValueError(f"Evaluation file is missing column(s): {', '.join(sorted(missing))}")
    if "review_id" not in df.columns:
        df["review_id"] = [f"EVAL-{i + 1:02d}" for i in range(len(df))]
    df["review_id"] = df["review_id"].astype(str)
    df["manual_sentiment"] = df["manual_sentiment"].astype(str).str.strip().str.capitalize()

    warnings = []
    bad = ~df["manual_sentiment"].isin(SENTIMENTS)
    if bad.any():
        warnings.append(f"{int(bad.sum())} row(s) had a manual label other than Positive/Neutral/Negative and were skipped.")
    df = df[~bad & df["feedback_text"].notna()].reset_index(drop=True)
    if df.empty:
        raise ValueError("No labelled reviews to evaluate.")

    analysed, info = analyze_dataframe(df[["review_id", "feedback_text"]], client=client)
    warnings += info["warnings"]
    df["predicted"] = analysed["sentiment"].values

    correct = int((df["predicted"] == df["manual_sentiment"]).sum())
    n = len(df)
    confusion = (pd.crosstab(df["manual_sentiment"], df["predicted"])
                 .reindex(index=SENTIMENTS, columns=SENTIMENTS, fill_value=0))
    confusion.index.name, confusion.columns.name = "Manual label", "Predicted"

    per_class = {}
    for label in SENTIMENTS:
        tp = int(confusion.loc[label, label])
        predicted_n = int(confusion[label].sum())
        actual_n = int(confusion.loc[label].sum())
        per_class[label] = {
            "precision": tp / predicted_n if predicted_n else None,
            "recall": tp / actual_n if actual_n else None,
            "support": actual_n,
        }

    mistakes = df.loc[df["predicted"] != df["manual_sentiment"],
                      ["review_id", "feedback_text", "manual_sentiment", "predicted"]].reset_index(drop=True)
    return {
        "n": n,
        "correct": correct,
        "accuracy": correct / n,
        "confusion": confusion,
        "per_class": per_class,
        "mistakes": mistakes,
        "method_label": info["method_label"],
        "warnings": warnings,
    }


def main() -> None:
    """python -m fiq.evaluation          rule-based fallback
       python -m fiq.evaluation --llm    Claude (needs ANTHROPIC_API_KEY; sends the 20 reviews to Anthropic)"""
    import sys
    from pathlib import Path

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
            sys.exit(f"Cannot run the LLM evaluation: {msg}")

    path = Path(__file__).resolve().parent.parent / "sample_data" / "eval_set_20.csv"
    ev = evaluate(pd.read_csv(path), client=client)
    for w in ev["warnings"]:
        print(f"WARNING: {w}")
    print(f"Method: {ev['method_label']}")
    print(f"Sentiment accuracy: {ev['correct']}/{ev['n']} = {ev['accuracy']:.0%}")
    print()
    print("Confusion matrix (rows = manual label, columns = predicted):")
    print(ev["confusion"].to_string())
    print()
    for label, m in ev["per_class"].items():
        p = "n/a" if m["precision"] is None else f"{m['precision']:.0%}"
        r = "n/a" if m["recall"] is None else f"{m['recall']:.0%}"
        print(f"{label:<9} precision {p:>4}  recall {r:>4}  support {m['support']}")
    print()
    print("Misclassified:")
    for _, row in ev["mistakes"].iterrows():
        print(f"  {row['review_id']}  manual {row['manual_sentiment']:<8} predicted {row['predicted']:<8} {row['feedback_text']}")


if __name__ == "__main__":
    main()

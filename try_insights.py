import pandas as pd

from fiq.insights import build_pain_points, build_recommendations, verify_all_quotes
from fiq.pipeline import analyze_dataframe
from fiq.validation import validate_reviews

clean, _ = validate_reviews(pd.read_csv("sample_data/synthetic_reviews_60.csv"))
df, info = analyze_dataframe(clean, client=None)  # rule-based on purpose, so the output is repeatable
print(info["method_label"])

points = build_pain_points(df)
recs = build_recommendations(points, len(df))

print()
print("--- pain points (ranked by negative reviews) ---")
for i, p in enumerate(points, 1):
    print(f"{i}. {p['theme']}: {p['negative']} negative of {p['total']}  [{p['evidence']}]")
    for q in p["quotes"]:
        print(f"     \"{q['quote']}\"  ({q['review_id']})")

print()
print("--- recommendations (score = impact / effort) ---")
for i, r in enumerate(recs, 1):
    print(f"{i}. [{r['priority']}] {r['theme']}  impact {r['impact_estimate']} / effort {r['effort_estimate']} = {r['score']}")
    print(f"     {r['recommendation']}")

print()
print("QUOTE AUDIT (every quote must be an exact substring of its review):", verify_all_quotes(points + recs, df))

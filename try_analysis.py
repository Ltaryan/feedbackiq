 import pandas as pd

from fiq.constants import THEMES, OTHER
from fiq.sentiment import rule_based_sentiment
from fiq.themes import assign_themes
from fiq.validation import validate_reviews

clean, _ = validate_reviews(pd.read_csv("sample_data/synthetic_reviews_60.csv"))
clean["sentiment"] = clean["feedback_text"].apply(rule_based_sentiment)
clean["theme_list"] = clean["feedback_text"].apply(assign_themes)

short = {t: t.split(" ")[0][:5].upper() for t in THEMES}
short[OTHER] = "OTHER"

print("--- every review: id, stars, sentiment, themes, text ---")
for _, r in clean.iterrows():
    tags = ",".join(short[t] for t in r["theme_list"])
    print(f"{r['review_id']}  {int(r['rating'])}*  {r['sentiment']:<8} {tags:<16} {r['feedback_text'][:70]}")

print()
print("--- sentiment counts ---")
print(clean["sentiment"].value_counts().to_string())
print()
print("--- theme counts (a review can have several) ---")
print(clean.explode("theme_list")["theme_list"].value_counts().to_string())

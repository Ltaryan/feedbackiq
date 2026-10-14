import pandas as pd
from fiq.validation import validate_reviews

raw = pd.read_csv("sample_data/synthetic_reviews_60.csv")
clean, report = validate_reviews(raw)
print("CLEAN FILE:", {k: v for k, v in report.items() if k not in ("excluded", "warnings")})

messy = pd.DataFrame({
    "review_id": ["A1", "A2", "A2", "A4", "A5", None],
    "date": ["2026-01-01", "2026-01-02", "2026-01-03", "oops", "2026-01-05", "2026-01-06"],
    "rating": [5, 9, 3, 4, "abc", 2],
    "feedback_text": ["Great food", "Cold fries", "Another review", "   ", "Great food", "Late delivery"],
})
clean2, report2 = validate_reviews(messy)
print("MESSY FILE:", {k: v for k, v in report2.items() if k not in ("excluded", "warnings")})
print(report2["excluded"][["review_id", "exclusion_reason"]].to_string(index=False))
print(report2["warnings"])

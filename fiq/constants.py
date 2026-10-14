"""Shared labels. Keeping them in one place stops typos between modules."""

SENTIMENTS = ["Positive", "Neutral", "Negative"]

THEMES = [
    "Delivery speed & ETA accuracy",
    "Food quality & temperature",
    "Missing or incorrect items",
    "Pricing, fees & offers",
    "Restaurant & menu availability",
    "App experience & checkout",
    "Refunds & customer support",
    "Packaging & order condition",
]
OTHER = "Other / Unclassified"
ALL_THEMES = THEMES + [OTHER]

METHOD_RULES = "Rule-based fallback"

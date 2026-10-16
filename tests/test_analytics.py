import pytest

from fiq.analytics import build_database, load_queries, run_all
from fiq.pipeline import analyze_dataframe


@pytest.fixture
def results(sample_clean):
    return run_all(analyze_dataframe(sample_clean)[0])


def test_every_query_has_a_question_and_runs(results):
    queries = load_queries()
    assert list(queries) == ["complaint_rate_by_order_type", "top_complaint_themes_by_month",
                             "sentiment_vs_star_rating", "themes_that_fail_together"]
    assert all(q["question"] for q in queries.values())
    assert all(len(results[name]) for name in queries)


def test_meal_orders_have_about_three_times_the_complaint_rate_of_snacks(results):
    rates = results["complaint_rate_by_order_type"].set_index("order_type")["negative_pct"]
    assert rates["Meal"] == 80 and rates["Snacks"] == 27
    assert rates.index[0] == "Meal"


def test_missing_items_is_top_or_tied_top_every_month(results):
    monthly = results["top_complaint_themes_by_month"]
    tops = monthly[monthly["rank_in_month"] == 1].groupby("month")["theme"].apply(set)
    assert list(tops.index) == ["2026-07", "2026-08", "2026-09"]
    assert all("Missing or incorrect items" in themes for themes in tops)


def test_text_sentiment_never_contradicts_star_rating(results):
    bands = results["sentiment_vs_star_rating"].set_index("rating_band")
    assert bands["contradictions"].sum() == 0
    assert (bands.loc["1-2 stars", "negative"], bands.loc["1-2 stars", "reviews"]) == (30, 35)
    assert (bands.loc["4-5 stars", "positive"], bands.loc["4-5 stars", "reviews"]) == (17, 18)


def test_missing_items_and_refunds_fail_together(results):
    pairs = results["themes_that_fail_together"]
    assert pairs.iloc[0][["theme_a", "theme_b", "negative_reviews"]].tolist() == [
        "Missing or incorrect items", "Refunds & customer support", 2]


def test_database_has_one_row_per_review_theme(sample_clean):
    df, _ = analyze_dataframe(sample_clean)
    con = build_database(df)
    assert con.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 60
    assert con.execute("SELECT COUNT(*) FROM review_themes").fetchone()[0] == df["theme_list"].str.len().sum()

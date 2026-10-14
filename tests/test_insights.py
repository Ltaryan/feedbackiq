import pandas as pd
import pytest

from fiq.insights import (build_pain_points, build_recommendations, extract_quote, impact_estimate,
                          verify_all_quotes)
from fiq.pipeline import analyze_dataframe


@pytest.fixture
def analysed(sample_clean):
    return analyze_dataframe(sample_clean)[0]


@pytest.fixture
def points(analysed):
    return build_pain_points(analysed)


def test_pain_point_ranking(points):
    top = [(p["theme"], p["negative"], p["total"]) for p in points[:5]]
    assert top == [
        ("Missing or incorrect items", 8, 10),
        ("App experience & checkout", 6, 11),
        ("Food quality & temperature", 6, 11),
        ("Refunds & customer support", 5, 7),
        ("Pricing, fees & offers", 4, 8),
    ]


def test_pain_point_review_ids_are_negative(points, analysed):
    neg_ids = set(analysed.loc[analysed["sentiment"] == "Negative", "review_id"])
    for p in points:
        assert len(p["review_ids"]) == p["negative"]
        assert set(p["review_ids"]) <= neg_ids


def test_every_quote_is_exact(points, analysed):
    recs = build_recommendations(points, len(analysed))
    assert verify_all_quotes(points + recs, analysed) == []


def test_verify_catches_altered_quote(points, analysed):
    broken = [{**points[0], "quotes": [{"review_id": points[0]["quotes"][0]["review_id"], "quote": "invented words"}]}]
    assert verify_all_quotes(broken, analysed) == ["Missing or incorrect items: quote not found in review "
                                                   + points[0]["quotes"][0]["review_id"]]


def test_verify_catches_unknown_review(analysed):
    problems = verify_all_quotes([{"theme": "T", "quotes": [{"review_id": "NOPE", "quote": "x"}]}], analysed)
    assert problems == ["T: quote cites unknown review NOPE"]


def test_extract_quote_picks_matching_sentence():
    text = "Lovely rider. But the fries were soggy! Will see."
    assert extract_quote(text, "Food quality & temperature") == "But the fries were soggy!"


def test_extract_quote_falls_back_to_first_sentence():
    assert extract_quote("Hmm. Okay.", "Pricing, fees & offers") == "Hmm."


@pytest.mark.parametrize("neg, n, expected", [(8, 60, 5), (6, 60, 4), (4, 60, 3), (2, 60, 2), (1, 60, 1), (0, 0, 1)])
def test_impact_estimate(neg, n, expected):
    assert impact_estimate(neg, n) == expected


def test_recommendations_ordered_by_score(points, analysed):
    recs = build_recommendations(points, len(analysed))
    assert [r["theme"] for r in recs][0] == "Missing or incorrect items"
    assert recs[0]["priority"] == "High" and recs[0]["score"] == 2.5
    assert [r["score"] for r in recs] == sorted((r["score"] for r in recs), reverse=True)


def test_recommendations_need_enough_evidence():
    df = pd.DataFrame({
        "review_id": ["a", "b"], "feedback_text": ["Cold food.", "Cold again."], "rating": [1, 1],
        "sentiment": ["Negative", "Negative"], "theme_list": [["Food quality & temperature"]] * 2,
    })
    points = build_pain_points(df)
    assert len(points) == 1 and points[0]["evidence"].startswith("Limited")
    assert build_recommendations(points, len(df)) == []


def test_empty_input_gives_no_points():
    assert build_pain_points(pd.DataFrame(columns=["review_id", "feedback_text", "sentiment", "theme_list"])) == []

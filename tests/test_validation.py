import pandas as pd
import pytest

from fiq.validation import validate_reviews


@pytest.fixture
def messy():
    return pd.DataFrame({
        "review_id": ["A1", "A2", "A2", "A4", "A5", None],
        "date": ["2026-01-01", "2026-01-02", "2026-01-03", "oops", "2026-01-05", "2026-01-06"],
        "rating": [5, 9, 3, 4, "abc", 2],
        "feedback_text": ["Great food", "Cold fries", "Another review", "   ", "Great food", "Late delivery"],
    })


def test_sample_file_is_clean(sample_raw):
    clean, report = validate_reviews(sample_raw)
    assert report["total_rows"] == 60
    assert report["valid_reviews"] == 60
    assert report["excluded_count"] == 0
    assert report["has_rating"] and report["has_date"] and report["has_order_type"]


def test_missing_text_column_raises():
    with pytest.raises(ValueError, match="feedback_text"):
        validate_reviews(pd.DataFrame({"review_id": [1], "rating": [5]}))


def test_column_aliases_are_accepted():
    clean, _ = validate_reviews(pd.DataFrame({"ID": ["x"], "Review": ["Nice and hot"]}))
    assert clean.loc[0, "review_id"] == "x"
    assert clean.loc[0, "feedback_text"] == "Nice and hot"


def test_exclusions_and_reasons(messy):
    clean, report = validate_reviews(messy)
    reasons = dict(zip(report["excluded"]["review_id"], report["excluded"]["exclusion_reason"]))
    assert reasons == {
        "A4": "Missing or empty feedback_text",
        "A2": "Duplicate review_id",
        "A5": "Duplicate feedback_text",
    }
    assert list(clean["review_id"]) == ["A1", "A2", "AUTO-7"]


def test_bad_rating_and_date_are_blanked_not_dropped(messy):
    clean, report = validate_reviews(messy)
    assert report["invalid_ratings"] == 1  # the 9; 'abc' was on an excluded duplicate row
    assert pd.isna(clean.loc[clean["review_id"] == "A2", "rating"]).all()
    assert report["invalid_dates"] == 0  # 'oops' belonged to the empty-text row


def test_source_row_points_to_original_file_line(messy):
    clean, _ = validate_reviews(messy)
    assert clean.loc[clean["review_id"] == "AUTO-7", "source_row"].item() == 7


def test_optional_columns_missing_gives_warnings():
    clean, report = validate_reviews(pd.DataFrame({"feedback_text": ["one", "two"]}))
    assert list(clean["review_id"]) == ["AUTO-2", "AUTO-3"]
    assert not report["has_rating"] and not report["has_date"] and not report["has_order_type"]
    assert len(report["warnings"]) == 3

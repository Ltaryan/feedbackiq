import pytest

from fiq.constants import OTHER, THEMES
from fiq.sentiment import rule_based_sentiment, sentiment_score
from fiq.themes import assign_themes


@pytest.mark.parametrize("text, expected", [
    ("Delicious food, hot and fresh, will order again.", "Positive"),
    ("The pasta was cold and soggy.", "Negative"),
    ("Received my order.", "Neutral"),
    ("The food was not good.", "Negative"),
    ("Not bad at all.", "Positive"),
    ("Ordered late at night, arrived quickly and hot.", "Positive"),
])
def test_rule_based_sentiment(text, expected):
    assert rule_based_sentiment(text) == expected


def test_complaints_weigh_more_than_praise():
    assert sentiment_score("good but cold") == pytest.approx(-0.5)


def test_sentiment_ignores_non_string_input():
    assert rule_based_sentiment(None) == "Neutral"


@pytest.mark.parametrize("text, theme", [
    ("ETA said 12 minutes but it took 40", THEMES[0]),
    ("The fries were soggy", THEMES[1]),
    ("They forgot my drink", THEMES[2]),
    ("The delivery fee is too high", THEMES[3]),
    ("Half the menu was unavailable", THEMES[4]),
    ("App crashed at checkout", THEMES[5]),
    ("Still waiting for my refund", THEMES[6]),
    ("The soup leaked everywhere", THEMES[7]),
])
def test_each_theme_is_detected(text, theme):
    assert theme in assign_themes(text)


def test_unmatched_text_is_other():
    assert assign_themes("Thanks!") == [OTHER]


def test_word_boundaries_prevent_false_matches():
    assert THEMES[0] not in assign_themes("Spending a lot lately")  # 'pending'/'late' inside other words
    assert THEMES[3] not in assign_themes("Feedback about the rider")  # 'fee' inside 'feedback'


def test_late_at_night_is_not_lateness():
    assert THEMES[0] not in assign_themes("Ordered late at night, all good.")

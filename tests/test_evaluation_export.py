import io

import pandas as pd
import pytest

from fiq.constants import SENTIMENTS
from fiq.evaluation import evaluate
from fiq.export import analysed_csv_bytes, report_markdown
from fiq.insights import build_pain_points, build_recommendations
from fiq.pipeline import analyze_dataframe


def test_rule_based_accuracy(eval_raw):
    ev = evaluate(eval_raw)
    assert (ev["correct"], ev["n"]) == (15, 20)
    assert ev["accuracy"] == pytest.approx(0.75)


def test_confusion_matrix(eval_raw):
    conf = evaluate(eval_raw)["confusion"]
    assert list(conf.index) == SENTIMENTS and list(conf.columns) == SENTIMENTS
    assert conf.values.tolist() == [[7, 0, 0], [2, 2, 1], [1, 1, 6]]


def test_mistakes_listed(eval_raw):
    ev = evaluate(eval_raw)
    assert len(ev["mistakes"]) == 5
    assert "EVAL-02" in set(ev["mistakes"]["review_id"])  # sarcasm is a known weakness


def test_evaluation_skips_bad_labels():
    ev = evaluate(pd.DataFrame({"feedback_text": ["Great food", "Cold"], "manual_sentiment": ["positive", "angry"]}))
    assert ev["n"] == 1 and ev["warnings"]


def test_evaluation_requires_label_column():
    with pytest.raises(ValueError, match="manual_sentiment"):
        evaluate(pd.DataFrame({"feedback_text": ["x"]}))


@pytest.fixture
def analysed(sample_clean):
    return analyze_dataframe(sample_clean)


def test_csv_export_round_trips(analysed):
    df, _ = analysed
    data = analysed_csv_bytes(df)
    assert data.startswith(b"\xef\xbb\xbf")  # BOM for Excel
    back = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig")
    assert len(back) == 60
    assert "theme_list" not in back.columns and "themes" in back.columns
    assert back.loc[0, "date"] == df.loc[0, "date"].strftime("%Y-%m-%d")


def test_markdown_report_contents(analysed, eval_raw):
    df, info = analysed
    points = build_pain_points(df)
    recs = build_recommendations(points, len(df))
    md = report_markdown(df, points, recs, info, sample=True, evaluation=evaluate(eval_raw))
    assert "Rule-based fallback" in md and "Synthetic data" in md
    assert "### 1. Missing or incorrect items" in md
    assert "15/20 = 75%" in md
    assert "| Positive | 7 | 0 | 0 |" in md


def test_markdown_report_without_evaluation(analysed):
    df, info = analysed
    md = report_markdown(df, [], [], info, sample=False)
    assert "Not run for this report." in md and "Synthetic data" not in md

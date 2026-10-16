"""End-to-end UI scenarios: the real app.py driven headlessly with Streamlit's AppTest (no browser needed)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
TABS = ["Dashboard", "Feedback", "Insights", "Recommendations", "Evaluation", "Export"]


@pytest.fixture
def at(monkeypatch):
    # empty (not deleted) so app.py's load_dotenv() cannot fill them from a local .env
    for var in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "FIQ_PROVIDER"):
        monkeypatch.setenv(var, "")
    return AppTest.from_file(APP, default_timeout=60).run()


def _button(at, text):
    return next(b for b in at.button if text in b.label)


def analyze_sample(at):
    _button(at, "Analyze reviews").click().run()
    return at


def upload(at, content: bytes, name="reviews.csv"):
    at.sidebar.radio[0].set_value("Upload my CSV").run()
    if content is not None:
        at.sidebar.file_uploader[0].set_value((name, content, "text/csv")).run()
    _button(at, "Analyze reviews").click().run()
    return at


def texts(elements):
    return " ".join(str(e.value) for e in elements)


def test_first_load_shows_instructions(at):
    assert not at.exception
    assert "Analyze reviews" in texts(at.info)


def test_sample_run_shows_banners_and_six_tabs(at):
    analyze_sample(at)
    assert not at.exception
    assert [t.label for t in at.tabs] == TABS
    assert "Synthetic data" in texts(at.warning) and "Rule-based fallback" in texts(at.warning)


def test_llm_option_hidden_without_key(at):
    assert not at.sidebar.checkbox
    assert "ANTHROPIC_API_KEY" in texts(at.sidebar.caption)


def test_llm_is_off_by_default_with_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("FIQ_PROVIDER", "")
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert app.sidebar.checkbox[0].value is False  # privacy: nothing is sent unless the user opts in


def test_upload_selected_but_no_file(at):
    upload(at, None)
    assert "Please upload a CSV first." in texts(at.sidebar.error)


def test_upload_valid_csv(at):
    csv = ("review_id,date,rating,feedback_text\n"
           "A1,2026-01-01,1,Order came 40 minutes late and cold\n"
           "A2,2026-01-03,5,Arrived early and piping hot\n"
           "A3,05/01/2026,2,They forgot my fries\n").encode()
    upload(at, csv)
    assert not at.exception and [t.label for t in at.tabs] == TABS
    assert "Synthetic data" not in texts(at.warning)
    assert "3 valid of 3 rows" in at.expander[0].label


def test_upload_without_feedback_column(at):
    upload(at, b"id,stars\n1,5\n")
    assert "feedback_text" in texts(at.sidebar.error) and not at.exception


def test_upload_empty_file(at):
    upload(at, b"")
    assert "That file is empty." in texts(at.sidebar.error)


def test_upload_header_only(at):
    upload(at, b"review_id,feedback_text\n")
    assert "No valid reviews remain" in texts(at.sidebar.error)


def test_upload_wrong_encoding(at):
    upload(at, "review_id,feedback_text\n1,caf\xe9 was cold\n".encode("cp1252"))
    assert at.sidebar.error and not at.exception  # a readable message, never a traceback


def test_upload_text_only_hides_charts_gracefully(at):
    upload(at, b"feedback_text\nCold food\nGreat app\n")
    assert not at.exception
    assert "Add a date column" in texts(at.info)


def test_filters_that_match_nothing(at):
    analyze_sample(at)
    at.multiselect[0].set_value([]).run()  # untick every sentiment
    assert "No reviews match the current filters." in texts(at.info)
    assert "Showing 0 of 60 reviews" in texts(at.caption)


def test_search_feedback(at):
    analyze_sample(at)
    at.text_input[0].set_value("refund").run()
    assert not at.exception
    assert any("review(s)" in c.value and not c.value.startswith("60") for c in at.caption)


def test_evaluation_tab(at):
    analyze_sample(at)
    _button(at, "rule-based").click().run()
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Sentiment accuracy"] == "75%" and metrics["Correct / total"] == "15 / 20"

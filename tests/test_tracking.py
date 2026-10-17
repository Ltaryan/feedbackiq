"""Mixpanel analytics: off by default, allow-listed properties only, and never any review text."""

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import fiq.tracking as tracking

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "synthetic_reviews_60.csv"


class FakeMixpanel:
    sent: list = []

    def __init__(self, token, consumer=None):
        self.token = token

    def track(self, distinct_id, event, props):
        FakeMixpanel.sent.append((distinct_id, event, props))


class SyncThread:
    """Run the background send immediately so tests can see it."""

    def __init__(self, target, daemon=None):
        self.target = target

    def start(self):
        self.target()


@pytest.fixture
def fake_mixpanel(monkeypatch):
    import mixpanel

    FakeMixpanel.sent = []
    monkeypatch.setenv("MIXPANEL_TOKEN", "test-token")
    monkeypatch.setattr(mixpanel, "Mixpanel", FakeMixpanel)
    monkeypatch.setattr(mixpanel, "Consumer", lambda **kw: None)
    monkeypatch.setattr(tracking, "threading", SimpleNamespace(Thread=SyncThread))
    st.cache_resource.clear()
    yield FakeMixpanel.sent
    st.cache_resource.clear()


def test_off_without_token(monkeypatch):
    monkeypatch.setenv("MIXPANEL_TOKEN", "")
    assert tracking.get_tracker() is None
    assert tracking.track(None, "s1", "analysis_run", {"reviews": 5}) is False


def test_only_allow_listed_properties_survive():
    props = tracking.safe_properties("analysis_run", {
        "reviews": 60, "method": "rules", "feedback_text": "Call me on 9876543210",
        "file_name": "secret.csv", "data_source": "x" * 100, "nested": {"a": 1},
    })
    assert props == {"reviews": 60, "method": "rules", "data_source": "x" * 40}


def test_unknown_events_are_rejected():
    sent = []
    tracker = SimpleNamespace(track=lambda *a: sent.append(a))
    assert tracking.track(tracker, "s1", "review_text_exported", {"reviews": 1}, background=False) is False
    assert tracking.track(tracker, "s1", "export_downloaded", {"format": "csv"}, background=False) is True
    assert sent == [("s1", "export_downloaded", {"format": "csv", "app": "FeedbackIQ"})]


def test_a_failing_mixpanel_never_breaks_the_app():
    def boom(*a):
        raise ConnectionError("Mixpanel down")

    assert tracking.track(SimpleNamespace(track=boom), "s1", "session_started", background=False) is True


def test_app_sends_the_funnel_events_and_no_review_text(fake_mixpanel, monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "FIQ_PROVIDER"):
        monkeypatch.setenv(var, "")
    app = AppTest.from_file(APP, default_timeout=60).run()
    next(b for b in app.button if "Analyze reviews" in b.label).click().run()
    next(b for b in app.button if "rule-based" in b.label).click().run()
    app.text_input[0].set_value("refund").run()
    assert not app.exception

    events = [event for _, event, _ in fake_mixpanel]
    assert events == ["session_started", "analysis_run", "evaluation_run", "feedback_searched"]
    assert len({sid for sid, _, _ in fake_mixpanel}) == 1  # one anonymous session id

    run = dict(fake_mixpanel[1][2])
    assert run == {"app": "FeedbackIQ", "data_source": "sample", "reviews": 60, "method": "rules",
                   "llm_requested": False, "excluded_rows": 0, "pain_points": 8}
    assert fake_mixpanel[2][2]["accuracy"] == 0.75

    texts = pd.read_csv(SAMPLE)["feedback_text"].tolist()
    sent_values = [str(v) for _, _, props in fake_mixpanel for v in props.values()]
    assert not any(t in v or v in t for t in texts for v in sent_values if len(v) > 12)
    assert "refund" not in sent_values  # the search text itself is never sent

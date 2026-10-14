import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from fiq.validation import validate_reviews

DATA = Path(__file__).resolve().parent.parent / "sample_data"


@pytest.fixture
def sample_raw():
    return pd.read_csv(DATA / "synthetic_reviews_60.csv")


@pytest.fixture
def sample_clean(sample_raw):
    return validate_reviews(sample_raw)[0]


@pytest.fixture
def eval_raw():
    return pd.read_csv(DATA / "eval_set_20.csv")


class FakeClient:
    """Stands in for anthropic.Anthropic(): replies with whatever `responder(prompt)` returns, as JSON text."""

    def __init__(self, responder, stop_reason="end_turn"):
        self.calls = []
        self._responder = responder
        self._stop = stop_reason
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        prompt = kwargs["messages"][0]["content"]
        payload = self._responder(prompt)
        if isinstance(payload, Exception):
            raise payload
        text = payload if isinstance(payload, str) else json.dumps(payload)  # a str is sent as-is (e.g. broken JSON)
        return SimpleNamespace(stop_reason=self._stop, content=[SimpleNamespace(type="text", text=text)])


@pytest.fixture
def fake_client():
    return FakeClient

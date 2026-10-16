import json

import pandas as pd

from fiq.constants import METHOD_RULES, OTHER, THEMES
from fiq.llm import METHOD_LLM, classify_reviews, get_llm_client, refine_recommendation_text
from fiq.pipeline import analyze_dataframe


def _label_all(sentiment="Negative", themes=(THEMES[2],)):
    def responder(prompt):
        reviews = json.loads(prompt.split("Reviews (JSON):\n", 1)[1])
        return {"reviews": [{"review_id": r["review_id"], "sentiment": sentiment, "themes": list(themes)}
                            for r in reviews]}
    return responder


def test_rule_based_pipeline_columns(sample_clean):
    df, info = analyze_dataframe(sample_clean)
    assert {"sentiment", "theme_list", "themes", "analysis_method"} <= set(df.columns)
    assert info["method_label"] == METHOD_RULES
    assert info["llm_reviews"] == 0 and info["rule_reviews"] == 60
    assert (df["analysis_method"] == METHOD_RULES).all()


def test_rule_based_sentiment_counts(sample_clean):
    df, _ = analyze_dataframe(sample_clean)
    assert df["sentiment"].value_counts().to_dict() == {"Negative": 33, "Positive": 17, "Neutral": 10}


def test_themes_text_matches_list(sample_clean):
    df, _ = analyze_dataframe(sample_clean)
    assert (df["themes"] == df["theme_list"].apply("; ".join)).all()


def test_no_api_key_means_no_client(monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "FIQ_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    client, msg = get_llm_client()
    assert client is None and "ANTHROPIC_API_KEY" in msg


def test_llm_labels_are_used(sample_clean, fake_client):
    client = fake_client(_label_all())
    df, info = analyze_dataframe(sample_clean, client=client)
    assert info["llm_reviews"] == 60 and info["method_label"] == METHOD_LLM
    assert (df["sentiment"] == "Negative").all()
    assert len(client.calls) == 3  # 60 reviews in batches of 20


def test_llm_failure_falls_back_to_rules(sample_clean, fake_client):
    client = fake_client(lambda prompt: RuntimeError("network down"))
    df, info = analyze_dataframe(sample_clean, client=client)
    assert info["llm_reviews"] == 0 and info["method_label"] == METHOD_RULES
    assert "fallback" in info["warnings"][0]


def test_invalid_llm_labels_are_rejected(fake_client):
    client = fake_client(lambda p: {"reviews": [
        {"review_id": "a", "sentiment": "Furious", "themes": []},
        {"review_id": "b", "sentiment": "Positive", "themes": ["Made-up theme", THEMES[1]]},
        {"review_id": "zzz", "sentiment": "Positive", "themes": []},
    ]})
    labels, warning = classify_reviews(client, [("a", "x"), ("b", "y")])
    assert labels == {"b": {"sentiment": "Positive", "themes": [THEMES[1]]}}
    assert "1 review" in warning


def test_llm_empty_themes_become_other(fake_client):
    clean = pd.DataFrame({"review_id": ["r1"], "feedback_text": ["Okay."]})
    df, _ = analyze_dataframe(clean, client=fake_client(_label_all("Neutral", ())))
    assert df.loc[0, "theme_list"] == [OTHER]


def test_refusal_is_treated_as_failure(fake_client):
    client = fake_client(_label_all(), stop_reason="refusal")
    labels, warning = classify_reviews(client, [("a", "x")])
    assert labels == {} and warning


def test_refine_keeps_numbers_and_quotes(fake_client):
    recs = [{"theme": THEMES[2], "recommendation": "old", "expected_benefit": "old", "rationale": "8 of 60",
             "score": 2.5, "quotes": [{"review_id": "SYN-017", "quote": "q"}], "text_source": "Rule-based template"}]
    client = fake_client(lambda p: {"items": [{"theme": THEMES[2], "recommendation": "new rec",
                                                "expected_benefit": "new benefit"}]})
    out, warn = refine_recommendation_text(client, recs)
    assert warn is None
    assert out[0]["recommendation"] == "new rec" and out[0]["score"] == 2.5 and out[0]["quotes"] == recs[0]["quotes"]
    assert out[0]["text_source"].startswith("LLM-refined")


def test_refine_failure_returns_original(fake_client):
    recs = [{"theme": THEMES[2], "recommendation": "old", "expected_benefit": "old", "rationale": "r"}]
    out, warn = refine_recommendation_text(fake_client(lambda p: ValueError("bad")), recs)
    assert out == recs and "not refined" in warn


# --------------------------------------------------------------------------- Gemini provider
from types import SimpleNamespace  # noqa: E402

from fiq.llm import GeminiClient, method_label  # noqa: E402


def _gemini(reply_text, finish="STOP"):
    client = GeminiClient.__new__(GeminiClient)  # skip the real SDK client
    client.model, client.label = "gemini-test", "Google Gemini LLM (gemini-test)"
    client.calls = []

    def generate_content(**kwargs):
        client.calls.append(kwargs)
        payload = reply_text(kwargs["contents"]) if callable(reply_text) else reply_text
        return SimpleNamespace(text=payload, candidates=[SimpleNamespace(finish_reason=finish)])

    client._client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    return client


def test_gemini_is_chosen_when_only_its_key_is_set(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("FIQ_PROVIDER", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-not-real")
    client, msg = get_llm_client()
    assert isinstance(client, GeminiClient) and "Gemini" in msg


def test_anthropic_wins_when_both_keys_are_set(monkeypatch):
    monkeypatch.delenv("FIQ_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-not-real")
    client, _ = get_llm_client()
    assert not isinstance(client, GeminiClient)


def test_gemini_labels_are_used_and_named(sample_clean):
    def reply(prompt):
        reviews = json.loads(prompt.split("Reviews (JSON):\n", 1)[1])
        return json.dumps({"reviews": [{"review_id": r["review_id"], "sentiment": "Negative", "themes": [THEMES[0]]}
                                       for r in reviews]})

    client = _gemini(reply)
    df, info = analyze_dataframe(sample_clean, client=client)
    assert info["llm_reviews"] == 60 and info["method_label"] == "Google Gemini LLM (gemini-test)"
    assert (df["analysis_method"] == method_label(client)).all()
    assert client.calls[0]["config"].response_json_schema["required"] == ["reviews"]  # same strict schema as Claude


def test_gemini_safety_block_falls_back(sample_clean):
    df, info = analyze_dataframe(sample_clean, client=_gemini("", finish="SAFETY"))
    assert info["llm_reviews"] == 0 and info["method_label"] == METHOD_RULES


def test_gemini_truncated_reply_falls_back():
    labels, warning = classify_reviews(_gemini('{"reviews": [', finish="MAX_TOKENS"), [("a", "Cold food")])
    assert labels == {} and warning

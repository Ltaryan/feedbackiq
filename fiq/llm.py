"""Optional Anthropic LLM layer. Everything here is optional: with no API key (or any API error) the
pipeline uses the rule-based fallback and says so.

Privacy: when the LLM is used, review text is sent to Anthropic's API. The app keeps it off by default.
"""

from __future__ import annotations

import json
import os

from .constants import SENTIMENTS, THEMES

MODEL = os.getenv("FIQ_MODEL", "claude-opus-5-5")
METHOD_LLM = f"Anthropic LLM ({MODEL})"
BATCH_SIZE = 20
MAX_LLM_REVIEWS = int(os.getenv("FIQ_MAX_LLM_REVIEWS", "500"))  # cost guard: the rest use the rule-based fallback
FALLBACK_BETA = "server-side-fallback-2026-07-01"

CLASSIFY_SYSTEM = (
    "You label customer reviews of a 10-minute food delivery app. For each review return its sentiment "
    "(Positive, Neutral or Negative, judged from the text only) and the themes it really talks about, chosen "
    "only from the allowed list. Use an empty theme list if none fit. Sarcasm counts as Negative. A review that "
    "mixes praise with a clear complaint is Negative."
)

_CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "reviews": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "review_id": {"type": "string"},
                    "sentiment": {"type": "string", "enum": SENTIMENTS},
                    "themes": {"type": "array", "items": {"type": "string", "enum": THEMES}},
                },
                "required": ["review_id", "sentiment", "themes"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["reviews"],
    "additionalProperties": False,
}

_REWRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string"},
                    "recommendation": {"type": "string"},
                    "expected_benefit": {"type": "string"},
                },
                "required": ["theme", "recommendation", "expected_benefit"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


def get_llm_client():
    """Return (client, message). client is None when the LLM cannot be used."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None, "No ANTHROPIC_API_KEY set, so the LLM is unavailable."
    try:
        import anthropic
    except ImportError:
        return None, "The 'anthropic' package is not installed, so the LLM is unavailable."
    return anthropic.Anthropic(), f"LLM available: {MODEL}"


def _ask_json(client, system: str, prompt: str, schema: dict, max_tokens: int = 8000) -> dict:
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        betas=[FALLBACK_BETA],
        fallbacks="default",  # if the model declines, the API retries on a fallback model
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("the model declined the request")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("the response was cut off")
    text = next((b.text for b in response.content if b.type == "text"), "")
    return json.loads(text)


def classify_reviews(client, rows: list[tuple[str, str]]):
    """Label (review_id, text) pairs. Returns ({review_id: {"sentiment", "themes"}}, warning or None).

    Batches that fail are left out of the result, so the caller can fall back to rules for those rows.
    """
    labels: dict[str, dict] = {}
    failed = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        prompt = (
            "Allowed themes:\n" + "\n".join(f"- {t}" for t in THEMES)
            + "\n\nReviews (JSON):\n"
            + json.dumps([{"review_id": rid, "text": text} for rid, text in batch], ensure_ascii=False)
        )
        try:
            data = _ask_json(client, CLASSIFY_SYSTEM, prompt, _CLASSIFY_SCHEMA)
        except Exception:  # noqa: BLE001 - any API/parse failure means "use the fallback for this batch"
            failed += len(batch)
            continue
        wanted = {rid for rid, _ in batch}
        for item in data.get("reviews", []):
            rid = str(item.get("review_id"))
            if rid not in wanted or item.get("sentiment") not in SENTIMENTS:
                continue
            themes = [t for t in dict.fromkeys(item.get("themes", [])) if t in THEMES]
            labels[rid] = {"sentiment": item["sentiment"], "themes": themes}
    missing = len(rows) - len(labels)
    warning = None
    if missing:
        warning = (f"The LLM did not return a usable label for {missing} review(s)"
                   + (f" ({failed} in failed requests)" if failed else "")
                   + "; the rule-based fallback was used for those.")
    return labels, warning


def refine_recommendation_text(client, recs: list[dict]):
    """Let the LLM reword recommendation text only. Counts, scores, quotes and IDs never change.
    Returns (recs, warning or None); on any failure the original recs are returned unchanged."""
    if not recs:
        return recs, None
    payload = [{"theme": r["theme"], "recommendation": r["recommendation"],
                "expected_benefit": r["expected_benefit"], "rationale": r["rationale"]} for r in recs]
    system = (
        "You polish product recommendations for a food delivery app. Rewrite each 'recommendation' and "
        "'expected_benefit' so they are concrete and specific to the rationale, in at most two sentences each. "
        "Do not invent numbers, percentages or facts. Keep the benefit phrased as a hypothesis. Keep each theme "
        "name exactly as given."
    )
    try:
        data = _ask_json(client, system, json.dumps(payload, ensure_ascii=False), _REWRITE_SCHEMA, max_tokens=4000)
    except Exception as e:  # noqa: BLE001
        return recs, f"Recommendation wording was not refined by the LLM ({type(e).__name__}); template text is shown."
    by_theme = {i["theme"]: i for i in data.get("items", [])}
    out = []
    for r in recs:
        new = by_theme.get(r["theme"])
        if new and new["recommendation"].strip() and new["expected_benefit"].strip():
            r = {**r, "recommendation": new["recommendation"].strip(),
                 "expected_benefit": new["expected_benefit"].strip(), "text_source": f"LLM-refined wording ({MODEL})"}
        out.append(r)
    return out, None

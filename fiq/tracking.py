"""Optional product analytics with Mixpanel.

Off unless MIXPANEL_TOKEN is set (in .env or Streamlit secrets). Privacy by design: only the events and
properties listed below can be sent, so review text, file names and personal details never leave the app.
Each browser session gets a random ID; no user identity is collected. Sending runs in a background thread
so a slow or unreachable Mixpanel never slows the app down.
"""

from __future__ import annotations

import os
import threading
import uuid

# event -> properties it may carry (everything else is dropped)
EVENTS: dict[str, set[str]] = {
    "session_started": set(),
    "analysis_run": {"data_source", "reviews", "method", "llm_requested", "excluded_rows", "pain_points"},
    "analysis_failed": {"data_source", "reason"},
    "evaluation_run": {"method", "accuracy"},
    "feedback_searched": {"results"},
    "export_downloaded": {"format"},
}
_SAFE_TYPES = (bool, int, float, str)
_MAX_STR = 40


def new_session_id() -> str:
    return uuid.uuid4().hex


def get_tracker():
    """Return a Mixpanel client, or None when analytics is off (no token or library missing)."""
    token = os.getenv("MIXPANEL_TOKEN", "").strip()
    if not token:
        return None
    try:
        from mixpanel import Consumer, Mixpanel
    except ImportError:
        return None
    host = os.getenv("MIXPANEL_API_HOST", "api.mixpanel.com")  # api-eu.mixpanel.com / api-in.mixpanel.com
    return Mixpanel(token, consumer=Consumer(api_host=host, request_timeout=3))


def safe_properties(event: str, props: dict | None) -> dict:
    """Keep only allow-listed, simple, short values."""
    allowed = EVENTS.get(event, set())
    out = {}
    for key, value in (props or {}).items():
        if key not in allowed or not isinstance(value, _SAFE_TYPES):
            continue
        out[key] = value[:_MAX_STR] if isinstance(value, str) else value
    return out


def track(tracker, session_id: str, event: str, props: dict | None = None, background: bool = True) -> bool:
    """Send one event. Returns False (and sends nothing) for unknown events or when analytics is off."""
    if tracker is None or event not in EVENTS:
        return False
    payload = {**safe_properties(event, props), "app": "FeedbackIQ"}

    def send():
        try:
            tracker.track(session_id, event, payload)
        except Exception:  # noqa: BLE001 - analytics must never break the app
            pass

    if background:
        threading.Thread(target=send, daemon=True).start()
    else:
        send()
    return True

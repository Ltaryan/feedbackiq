"""Mask contact and payment details in review text before it is shown, exported or sent to an LLM.

Covers emails, UPI IDs, card-like numbers and Indian phone numbers. Names are NOT detected; remove them before upload.
"""

from __future__ import annotations

import re

_RULES = [  # order matters: emails before UPI IDs, cards before phones
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[email]"),
    (re.compile(r"\b[\w.-]{2,}@[a-z]{2,}\b", re.I), "[upi id]"),
    (re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"), "[card number]"),
    (re.compile(r"(?<!\d)(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), "[phone]"),
]


def mask_pii(text: str) -> tuple[str, int]:
    """Return (masked_text, number_of_items_masked)."""
    total = 0
    for pattern, label in _RULES:
        text, n = pattern.subn(label, text)
        total += n
    return text, total

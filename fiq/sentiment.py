"""Rule-based sentiment: a transparent word-list baseline (also the fallback when no LLM is available).

It reads the text only (never the star rating). Known weaknesses: sarcasm, mixed reviews, words that
are not in the lists. Weights: a complaint word counts 1.5, a praise word 1.0, because complaints tend
to be stated more strongly. A negator ('not', 'no', ...) within the two previous words flips a word.
"""

from __future__ import annotations

import re

POS_STEMS = (
    "love", "great", "excellent", "amazing", "awesome", "perfect", "fresh", "crisp", "delicious", "tasty",
    "flavour", "flavor", "fastest", "quick", "accura", "smooth", "easy", "easi", "clean", "neat", "sturdy",
    "intact", "helpful", "polite", "friendly", "superb", "brilliant", "impress", "appreciat", "thank",
    "happy", "pleased", "satisf", "resolv", "steaming", "genuine",
)
POS_EXACT = {"good", "hot", "fast", "early", "best", "nice"}  # "fine" and "okay" are neutral on purpose
POS_PHRASES = ("on time", "piping hot", "no complaints")

NEG_STEMS = (
    "stale", "soggy", "lukewarm", "undercook", "overcook", "burnt", "spoil", "bland", "watery", "delay",
    "slow", "stuck", "missing", "forgot", "wrong", "spill", "leak", "crush", "crack", "damag", "torn",
    "cancel", "unavailable", "crash", "froze", "freez", "glitch", "bug", "confus", "terrible", "awful",
    "worst", "horrible", "rude", "ignor", "refus", "expensive", "overcharg", "hidden", "ridiculous",
    "annoy", "frustrat", "disappoint", "waste", "nobody", "unresponsive", "complain", "mistake", "fail",
    "error", "hate", "disgust", "forever", "overpriced", "never",
)
NEG_EXACT = {"cold", "late", "raw", "bad", "poor", "lost", "ages", "wait", "waiting"}
NEG_PHRASES = ("out of stock", "sold out", "not delivered")

NEGATORS = {"not", "no", "nothing", "without", "isn't", "wasn't", "don't", "didn't", "doesn't", "hardly"}

POS_WEIGHT, NEG_WEIGHT, THRESHOLD = 1.0, 1.5, 0.5


def sentiment_score(text: str) -> float:
    lowered = str(text).lower().replace("’", "'")
    for harmless in ("late at night", "late night", "late-night"):  # time of day, not lateness
        lowered = lowered.replace(harmless, " ")
    score = 0.0
    for phrase in POS_PHRASES:
        score += POS_WEIGHT * lowered.count(phrase)
    for phrase in NEG_PHRASES:
        score -= NEG_WEIGHT * lowered.count(phrase)
    words = re.findall(r"[a-z']+", lowered)
    for i, word in enumerate(words):
        negated = any(w in NEGATORS for w in words[max(0, i - 2):i])
        if word in POS_EXACT or word.startswith(POS_STEMS):
            score += -NEG_WEIGHT if negated else POS_WEIGHT
        elif word in NEG_EXACT or word.startswith(NEG_STEMS):
            score += POS_WEIGHT if negated else -NEG_WEIGHT
    return score


def rule_based_sentiment(text: str) -> str:
    score = sentiment_score(text)
    if score >= THRESHOLD:
        return "Positive"
    if score <= -THRESHOLD:
        return "Negative"
    return "Neutral"

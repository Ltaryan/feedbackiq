"""Rule-based theme assignment. A theme is only assigned when one of its patterns really appears in the
review text, and every pattern must start at a word boundary (so 'pending' does not match 'spending').
A review can have several themes. If nothing matches it is 'Other / Unclassified'."""

from __future__ import annotations

import re

from .constants import OTHER, THEMES

_RAW = {
    THEMES[0]: [  # delivery speed & ETA
        r"\beta\b", r"\b(\d+|ten|twenty|thirty|forty|a couple of|few) ?(minutes?|mins?)\b", r"\barriv\w* (late|early|after|in|within|before|on)\b", r"\blate\b(?! (at )?night)", r"\bearly\b", r"\bspeed\b",
        r"\bfastest\b", r"\bfast delivery\b", r"\bquick delivery\b", r"\bon time\b", r"\bpromised\b",
        r"\bestimated\b", r"\btracking\b", r"\bdelay", r"\bdelivered in\b", r"\bdelivery (took|time)\b",
    ],
    THEMES[1]: [  # food quality & temperature
        r"\bcold\b", r"\bhot\b", r"\bwarm\b", r"\blukewarm\b", r"\bsoggy\b", r"\bstale\b", r"\bfresh",
        r"\btaste", r"\btasty\b", r"\bdelicious\b", r"\bflavo", r"\bundercooked\b", r"\bovercooked\b",
        r"\bburnt\b", r"\braw\b", r"\bcrisp", r"\bbland\b", r"\bspoiled\b", r"\bwatery\b", r"\bchilled\b",
        r"\bportion",
    ],
    THEMES[2]: [  # missing or incorrect items
        r"\bmissing\b", r"\bforgot", r"\bwrong\b", r"\bsomeone else'?s\b", r"\breceived (one|only|half)\b",
        r"\bcame with\b", r"\bincorrect\b", r"\bmistake\b", r"\bcomplete\b", r"\bexactly as\b",
        r"\baccuracy\b", r"\bcorrect\b",
    ],
    THEMES[3]: [  # pricing, fees & offers
        r"\bfees?\b", r"\bcharge[ds]?\b", r"\bprices?\b", r"\bpriced?\b", r"\bpricing\b", r"\bexpensive\b",
        r"\boverpriced\b", r"\bcosts?\b", r"\boffers?\b", r"\bdiscount", r"\bcoupon", r"\bpromo",
        r"\bdeals?\b", r"\bsurcharge\b", r"\bsurge\b", r"\btoo much\b", r"\btotal\b",
    ],
    THEMES[4]: [  # restaurant & menu availability
        r"\bunavailable\b", r"\bout of stock\b", r"\bsold out\b", r"\bmenu\b", r"\bclosed\b",
        r"\bnot available\b", r"\bavailable\b", r"\bvariety\b", r"\boptions\b", r"\boutlets?\b",
        r"\bcancel", r"\bchoices\b", r"\blimited\b",
    ],
    THEMES[5]: [  # app experience & checkout
        r"\bapp\b", r"\bcheckout\b", r"\bcrash", r"\bfroze\b", r"\bfreez", r"\blogged out\b", r"\blog ?in\b",
        r"\bsearch\b", r"\bfilters?\b", r"\bui\b", r"\binterface\b", r"\bcart\b", r"\baddress", r"\bspinning\b",
        r"\bpayment page\b", r"\bglitch", r"\bbug", r"\breorder",
    ],
    THEMES[6]: [  # refunds & customer support
        r"\brefunds?\b", r"\bsupport\b", r"\bcustomer (care|service)\b", r"\bagent\b", r"\bticket",
        r"\breplied\b", r"\breplies\b", r"\brespond", r"\bcompensat",
    ],
    THEMES[7]: [  # packaging & order condition
        r"\bpackag", r"\bleak", r"\bspill", r"\bcrush", r"\bcrack", r"\bboxes\b", r"\bbox\b", r"\bseal",
        r"\btamper\b", r"\bintact\b", r"\bcontainer\b", r"\bsoaked\b", r"\bthrown around\b", r"\bdamag",
        r"\btorn\b", r"\bsquash",
    ],
}
PATTERNS = {theme: [re.compile(p, re.I) for p in pats] for theme, pats in _RAW.items()}


def theme_hits(text: str, theme: str) -> int:
    return sum(1 for p in PATTERNS[theme] if p.search(text))


def assign_themes(text: str) -> list[str]:
    found = [t for t in THEMES if theme_hits(text, t) > 0]
    return found or [OTHER]

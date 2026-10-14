"""Input validation: turn an uploaded CSV into a clean table and say exactly what was removed."""

from __future__ import annotations

import pandas as pd

from .privacy import mask_pii

ALIASES = {
    "review": "feedback_text", "text": "feedback_text", "feedback": "feedback_text",
    "comment": "feedback_text", "id": "review_id",
}
EXPECTED = ["review_id", "date", "rating", "feedback_text", "order_type"]


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    cols = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df.columns = [ALIASES.get(c, c) for c in cols]
    return df


def validate_reviews(df_raw: pd.DataFrame):
    """Return (clean_df, report).

    Rules:
      * `feedback_text` is mandatory (ValueError if missing).
      * Rows with empty text are excluded; duplicate review_ids and duplicate texts are excluded
        (first occurrence is kept).
      * A rating outside 1-5 or not a number is blanked (row kept). Unparseable dates are blanked.
      * Missing review_ids are generated (AUTO-<row>) so every insight can still point to a row.
    """
    df = _normalise_columns(df_raw).reset_index(drop=True)
    warnings: list[str] = []
    if "feedback_text" not in df.columns:
        raise ValueError(
            "No feedback column found. The CSV needs a 'feedback_text' column "
            "(expected columns: review_id, date, rating, feedback_text, optional order_type)."
        )
    df["source_row"] = df.index + 2  # row number in the original file (row 1 is the header)
    total_rows = len(df)
    excluded_parts = []

    # review_id: fill gaps / create the column
    auto_ids = 0
    if "review_id" not in df.columns:
        df["review_id"] = None
        warnings.append("No review_id column: IDs were generated (AUTO-<row>).")
    raw_ids = df["review_id"]
    if pd.api.types.is_float_dtype(raw_ids) and (raw_ids.dropna() % 1 == 0).all():
        raw_ids = raw_ids.astype("Int64")  # a blank cell makes pandas read 1,2,3 as 1.0,2.0,3.0
    ids = raw_ids.astype("string").str.strip()
    missing_id = ids.isna() | (ids == "")
    auto_ids = int(missing_id.sum())
    ids = ids.mask(missing_id, "AUTO-" + df["source_row"].astype(str))
    df["review_id"] = ids.astype(str)
    if auto_ids and "review_id" in df_raw.columns.str.lower().str.strip():
        warnings.append(f"{auto_ids} row(s) had no review_id; IDs were generated.")

    # empty text
    text = df["feedback_text"].astype("string")
    empty = text.isna() | (text.str.strip() == "")
    if empty.any():
        excluded_parts.append(df[empty].assign(exclusion_reason="Missing or empty feedback_text"))
    df = df[~empty].copy()
    df["feedback_text"] = df["feedback_text"].astype(str).str.strip()

    # personal details: masked here so the dashboard, LLM and exports only ever see masked text
    masked = df["feedback_text"].map(mask_pii)
    df["feedback_text"] = masked.str[0]
    pii_masked = int((masked.str[1] > 0).sum())
    if pii_masked:
        warnings.append(f"{pii_masked} review(s) contained phone numbers, emails, UPI IDs or card numbers; "
                        "these were masked.")

    # duplicate review ids
    dup_id = df["review_id"].duplicated(keep="first")
    if dup_id.any():
        excluded_parts.append(df[dup_id].assign(exclusion_reason="Duplicate review_id"))
    df = df[~dup_id].copy()

    # duplicate texts (same words, ignoring case and spacing)
    key = df["feedback_text"].str.lower().str.replace(r"\s+", " ", regex=True)
    dup_text = key.duplicated(keep="first")
    if dup_text.any():
        excluded_parts.append(df[dup_text].assign(exclusion_reason="Duplicate feedback_text"))
    df = df[~dup_text].copy()

    # rating
    invalid_ratings = 0
    if "rating" in df.columns:
        raw = df["rating"]
        num = pd.to_numeric(raw, errors="coerce")
        bad = raw.notna() & (num.isna() | (num < 1) | (num > 5))
        invalid_ratings = int(bad.sum())
        df["rating"] = num.mask(bad)
    else:
        df["rating"] = float("nan")
        warnings.append("No rating column: rating charts and filters are hidden.")

    # date
    invalid_dates = 0
    if "date" in df.columns:
        raw = df["date"]
        # ISO dates first; anything else (05/01/2026, 5 Jan 2026) is read day-first, as is usual in India
        parsed = pd.to_datetime(raw, errors="coerce", format="ISO8601")
        rest = raw.notna() & parsed.isna()
        if rest.any():
            parsed = parsed.mask(rest, pd.to_datetime(raw[rest].astype(str), errors="coerce", format="mixed", dayfirst=True))
        invalid_dates = int((raw.notna() & parsed.isna()).sum())
        df["date"] = parsed
    else:
        df["date"] = pd.NaT
        warnings.append("No date column: the volume-over-time chart is hidden.")

    if "order_type" not in df.columns:
        df["order_type"] = None
    df["order_type"] = df["order_type"].astype("string").fillna("Unknown").astype(str)

    if invalid_ratings:
        warnings.append(f"{invalid_ratings} rating value(s) were not numbers from 1 to 5 and were blanked.")
    if invalid_dates:
        warnings.append(f"{invalid_dates} date value(s) could not be read and were blanked.")

    clean = df[["review_id", "date", "rating", "feedback_text", "order_type", "source_row"]
               + [c for c in df.columns if c == "manual_sentiment"]].reset_index(drop=True)
    excluded = (
        pd.concat(excluded_parts)[["source_row", "review_id", "feedback_text", "exclusion_reason"]]
        if excluded_parts else pd.DataFrame(columns=["source_row", "review_id", "feedback_text", "exclusion_reason"])
    )
    report = {
        "total_rows": total_rows,
        "valid_reviews": len(clean),
        "excluded_count": len(excluded),
        "excluded": excluded.reset_index(drop=True),
        "invalid_ratings": invalid_ratings,
        "invalid_dates": invalid_dates,
        "auto_ids": auto_ids,
        "pii_masked": pii_masked,
        "has_rating": bool(clean["rating"].notna().any()),
        "has_date": bool(clean["date"].notna().any()),
        "has_order_type": bool((clean["order_type"] != "Unknown").any()),
        "warnings": warnings,
    }
    return clean, report

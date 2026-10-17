# Tracking plan (Mixpanel)

Product analytics for FeedbackIQ, implemented in [`fiq/tracking.py`](../fiq/tracking.py). It is **off unless `MIXPANEL_TOKEN` is set** (in `.env` locally, or Streamlit secrets when deployed).

## Questions it answers

1. Do visitors actually run an analysis, or leave after landing? (activation)
2. Do people use the sample or upload their own data? (real-use signal)
3. Is the Evaluation tab used? Do people trust the AI enough to export? (feature value)
4. Which upload errors happen most? (onboarding friction)

## Events

| Event | When it fires | Properties |
|---|---|---|
| `session_started` | First load of a browser session | none |
| `analysis_run` | An analysis finishes | `data_source` (sample / upload), `reviews`, `method` (rules / llm / mixed), `llm_requested`, `excluded_rows`, `pain_points` |
| `analysis_failed` | An upload can't be analysed | `data_source`, `reason` (empty_file / missing_column / no_valid_reviews / encoding) |
| `evaluation_run` | An evaluation button is used | `method` (rules / llm), `accuracy` |
| `feedback_searched` | A new search in the Feedback tab | `results` (count only) |
| `export_downloaded` | A download button is clicked | `format` (csv / markdown) |

Every event also carries `app = FeedbackIQ`.

## Privacy rules (enforced in code and tests)

- **Allow-list:** only the properties above can be sent; anything else is dropped before sending.
- **Never sent:** review text, search text, file names, personal details.
- **Anonymous:** each browser session gets a random ID; no login, no user identity.
- A failing or slow Mixpanel never affects the app (sent in the background, errors ignored).
- Tested in `tests/test_tracking.py`, including an end-to-end check that no review text is ever sent.

## Reports to build in Mixpanel

| Report | Setup | Answers |
|---|---|---|
| **Activation funnel** | `session_started` → `analysis_run` → `export_downloaded` | Where visitors drop off |
| **Feature usage** | Insights: count of `evaluation_run`, `feedback_searched`, `export_downloaded` per week | Which features earn their place |
| **Real-data share** | `analysis_run` broken down by `data_source` | Are people bringing their own data? |
| **Upload friction** | `analysis_failed` broken down by `reason` | What to fix in onboarding first |
| **AI adoption** | `analysis_run` broken down by `method` | How often the LLM is chosen |

## Metric definitions

- **Activation rate** = sessions with `analysis_run` ÷ sessions.
- **Export rate** = sessions with `export_downloaded` ÷ sessions with `analysis_run`.
- **Upload failure rate** = `analysis_failed` (upload) ÷ all upload attempts.

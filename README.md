# FeedbackIQ

A customer-feedback analyser for a 10-minute food delivery app. Upload reviews as a CSV (or use the synthetic sample) and get sentiment, recurring themes, ranked pain points with verified quotes, prioritised recommendations, an accuracy check against hand labels, and downloadable reports.

> Independent portfolio project. Not affiliated with any delivery company. The bundled data is synthetic.

## What it does

| Step | Module | Notes |
|---|---|---|
| Validate the CSV | `fiq/validation.py` | Reports every excluded row and why (empty text, duplicate ID, duplicate text). Bad ratings and dates are blanked, not dropped. |
| Privacy | `fiq/privacy.py` | Masks phone numbers, emails, UPI IDs and card numbers before anything is shown, exported or sent to the LLM. Names are not detected. |
| Sentiment | `fiq/sentiment.py` | Transparent word-list baseline that reads the text only, never the star rating. |
| Themes | `fiq/themes.py` | 8 delivery-app themes plus *Other / Unclassified*. A review can have several. |
| Optional LLM | `fiq/llm.py` | Anthropic Claude labels sentiment and themes with structured JSON output. Off by default; any failure falls back to rules, row by row. |
| Pipeline | `fiq/pipeline.py` | Records which method labelled each review. |
| Insights | `fiq/insights.py` | Pain points ranked by negative-review count. Every quote is an exact sentence from its source review, checked by `verify_all_quotes`. |
| Evaluation | `fiq/evaluation.py` | Accuracy, confusion matrix and per-class precision/recall on a separate 20-review labelled set. |
| Export | `fiq/export.py` | Analysed CSV and a Markdown report. |
| Dashboard | `app.py` | Streamlit app with six tabs: Dashboard, Feedback, Insights, Recommendations, Evaluation, Export. |

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

In the sidebar choose **Synthetic sample** and click **Analyze reviews**. No API key is needed.

### Optional: use Claude

```bash
copy .env.example .env          # macOS/Linux: cp .env.example .env
```

Put your key in `.env` (`ANTHROPIC_API_KEY=...`), restart the app and tick **Use Anthropic LLM**. Review text (with contact details masked) is then sent to Anthropic's API, so use synthetic or approved data only. At most 500 reviews are sent per run (`FIQ_MAX_LLM_REVIEWS`); the rest use the rule-based fallback.

## CSV format

| Column | Required | Notes |
|---|---|---|
| `feedback_text` | yes | Also accepted: `review`, `text`, `feedback`, `comment` |
| `review_id` | no | Generated as `AUTO-<row>` if missing |
| `date` | no | Enables the volume-over-time chart |
| `rating` | no | 1-5; shown for comparison, not used to predict sentiment |
| `order_type` | no | Enables the order-type filter |

## Command-line checks

```bash
python try_insights.py          # pain points, recommendations, quote audit
python -m fiq.evaluation        # rule-based accuracy on the 20-review set (15/20 = 75%)
python -m pytest                # test suite
```

## Results on the synthetic sample (rule-based)

- Top pain point: *Missing or incorrect items* (8 of 10 mentions negative), then App experience, Food quality, Refunds and Pricing.
- Sentiment accuracy on the evaluation set: 15/20 = 75%. The misses are sarcasm, mild complaints with no negative words, and neutral reviews that contain "fine" or "on time".

## Limitations

- The rule-based baseline misses sarcasm and reviews that mix praise with a complaint.
- The evaluation set is small (20 reviews; one mistake = 5 points), synthetic, and labelled by the author, so treat it as a demonstration, not a benchmark.
- Recommendations are hypotheses. Impact and effort are heuristic estimates, not predicted business outcomes.

## Documents

- [Product requirements (PRD)](docs/PRD.md)

## Project layout

```
fiq/            analysis package
tests/          pytest suite
sample_data/    synthetic reviews (60) and labelled evaluation set (20)
app.py          Streamlit dashboard
try_*.py        small scripts that print each stage
```

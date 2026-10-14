"""FeedbackIQ for a 10-minute food delivery app: Streamlit dashboard.

Run:  streamlit run app.py
Independent portfolio project. Not affiliated with any delivery company. Demo data is synthetic.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

try:  # optional: loads ANTHROPIC_API_KEY from a local .env file
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from fiq.constants import ALL_THEMES, OTHER, SENTIMENTS
from fiq.evaluation import evaluate
from fiq.export import analysed_csv_bytes, report_markdown
from fiq.insights import build_pain_points, build_recommendations, verify_all_quotes
from fiq.llm import get_llm_client, refine_recommendation_text
from fiq.pipeline import analyze_dataframe
from fiq.validation import validate_reviews

ROOT = Path(__file__).parent
SAMPLE = ROOT / "sample_data" / "synthetic_reviews_60.csv"
EVAL = ROOT / "sample_data" / "eval_set_20.csv"
COLORS = {"Positive": "#16a34a", "Neutral": "#94a3b8", "Negative": "#dc2626"}

st.set_page_config(page_title="FeedbackIQ", page_icon="📊", layout="wide")
st.markdown(
    "<style>.block-container{max-width:1250px;padding-top:2rem}"
    ".fiq-sub{opacity:.7;margin-top:-.6rem}</style>",
    unsafe_allow_html=True,
)
st.title("FeedbackIQ")
st.markdown('<p class="fiq-sub">Customer feedback analyser for a 10-minute food delivery app</p>', unsafe_allow_html=True)

# ------------------------------------------------------------------ sidebar
llm_client, llm_msg = get_llm_client()
with st.sidebar:
    st.header("1. Data")
    source = st.radio("Source", ["Synthetic sample (60 reviews)", "Upload my CSV"])
    uploaded = None
    if source == "Upload my CSV":
        uploaded = st.file_uploader("CSV with review_id, date, rating, feedback_text (optional: order_type)", type=["csv"])
        st.caption("Only upload data you have the right to analyse. Remove personal details first.")
    if SAMPLE.exists():
        st.download_button("Download sample dataset", SAMPLE.read_bytes(), "synthetic_reviews_60.csv", "text/csv", width="stretch")

    st.header("2. AI")
    use_llm = False
    if llm_client:
        use_llm = st.checkbox("Use Anthropic LLM", value=False,
                              help="Off by default. When on, review text is sent to Anthropic's API.")
        if use_llm:
            st.warning("Review text will be sent to an external provider (Anthropic). Use synthetic or approved data only.")
    else:
        st.caption(llm_msg)
    st.caption("Without the LLM, a clearly labelled rule-based fallback is used.")
    run = st.button("Analyze reviews", type="primary", width="stretch")

if run:
    try:
        if source == "Upload my CSV":
            if uploaded is None:
                st.sidebar.error("Please upload a CSV first.")
                st.stop()
            raw = pd.read_csv(uploaded)
        else:
            raw = pd.read_csv(SAMPLE)
        clean, report = validate_reviews(raw)
        if clean.empty:
            raise ValueError("No valid reviews remain after validation.")
        with st.spinner("Analyzing..."):
            client = llm_client if use_llm else None
            df, info = analyze_dataframe(clean, client=client)
            points = build_pain_points(df)
            recs = build_recommendations(points, len(df))
            if client is not None and info["llm_reviews"]:
                recs, warn = refine_recommendation_text(client, recs)
                if warn:
                    info["warnings"].append(warn)
            quote_problems = verify_all_quotes(points + recs, df)
        st.session_state["res"] = dict(raw=raw, clean=clean, df=df, info=info, report=report, points=points,
                                       recs=recs, quote_problems=quote_problems, sample=source != "Upload my CSV",
                                       evaluation=None)
    except pd.errors.EmptyDataError:
        st.sidebar.error("That file is empty.")
    except (ValueError, UnicodeDecodeError) as e:
        st.sidebar.error(str(e))

res = st.session_state.get("res")
if not res:
    st.info("Choose a data source in the sidebar and click **Analyze reviews**. The synthetic sample needs no setup.")
    st.stop()

df, info, report = res["df"], res["info"], res["report"]

# ------------------------------------------------------------------ banners
if res["sample"]:
    st.warning("**Synthetic data.** These reviews were written for a portfolio demo. They are not real customer feedback, "
               "and this project is not affiliated with any delivery company.")
if info["llm_reviews"]:
    st.info(f"Method: **{info['method_label']}**. Review text was sent to the Anthropic API.")
else:
    st.warning(f"Method: **{info['method_label']}**")
for w in info["warnings"] + report["warnings"]:
    st.caption(f"Note: {w}")
if res["quote_problems"]:
    st.error("Quote check failed: " + "; ".join(res["quote_problems"]))

with st.expander(f"Data preview and validation: {report['valid_reviews']} valid of {report['total_rows']} rows"):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows in file", report["total_rows"])
    c2.metric("Valid reviews", report["valid_reviews"])
    c3.metric("Excluded rows", report["excluded_count"])
    c4.metric("Blanked rating/date values", report["invalid_ratings"] + report["invalid_dates"])
    st.dataframe(res["clean"].head(10), hide_index=True, width="stretch")
    if report["excluded_count"]:
        st.markdown("**Excluded rows**")
        st.dataframe(report["excluded"], hide_index=True, width="stretch")

# ------------------------------------------------------------------ filters
f1, f2, f3 = st.columns(3)
sel_sent = f1.multiselect("Sentiment", SENTIMENTS, default=SENTIMENTS)
sel_theme = f2.multiselect("Theme (empty = all)", ALL_THEMES)
sel_type = f3.multiselect("Order type (empty = all)", sorted(df["order_type"].unique())) if report["has_order_type"] else []
g1, g2 = st.columns(2)
rating_range = g1.slider("Rating", 1, 5, (1, 5)) if report["has_rating"] else None
date_range = None
if report["has_date"]:
    dmin, dmax = df["date"].min().date(), df["date"].max().date()
    if dmin < dmax:
        date_range = g2.slider("Date range", dmin, dmax, (dmin, dmax))

view = df[df["sentiment"].isin(sel_sent)]
if sel_theme:
    view = view[view["theme_list"].apply(lambda t: any(x in t for x in sel_theme))]
if sel_type:
    view = view[view["order_type"].isin(sel_type)]
if rating_range and rating_range != (1, 5):
    view = view[view["rating"].between(*rating_range)]
if date_range:
    view = view[view["date"].isna() | view["date"].dt.date.between(*date_range)]
st.caption(f"Showing {len(view)} of {len(df)} reviews")

tabs = st.tabs(["Dashboard", "Feedback", "Insights", "Recommendations", "Evaluation", "Export"])

# ------------------------------------------------------------------ dashboard
with tabs[0]:
    if view.empty:
        st.info("No reviews match the current filters.")
    else:
        n = len(view)
        pct = view["sentiment"].value_counts().reindex(SENTIMENTS, fill_value=0) / n * 100
        k = st.columns(5)
        k[0].metric("Reviews", n)
        k[1].metric("Average rating", f"{view['rating'].mean():.2f}" if view["rating"].notna().any() else "n/a")
        k[2].metric("Positive", f"{pct['Positive']:.0f}%")
        k[3].metric("Neutral", f"{pct['Neutral']:.0f}%")
        k[4].metric("Negative", f"{pct['Negative']:.0f}%")

        a, b = st.columns(2)
        with a:
            st.subheader("Review volume over time")
            if report["has_date"] and view["date"].notna().any():
                vol = view.dropna(subset=["date"]).assign(week=lambda d: d["date"].dt.to_period("W").dt.start_time)
                vol = vol.groupby(["week", "sentiment"]).size().reset_index(name="reviews")
                st.plotly_chart(px.bar(vol, x="week", y="reviews", color="sentiment", color_discrete_map=COLORS,
                                       category_orders={"sentiment": SENTIMENTS}), width="stretch")
            else:
                st.info("Add a date column to see volume over time.")
        with b:
            st.subheader("Sentiment distribution")
            counts = view["sentiment"].value_counts().reindex(SENTIMENTS, fill_value=0)
            st.plotly_chart(px.pie(names=counts.index, values=counts.values, hole=0.5, color=counts.index,
                                   color_discrete_map=COLORS), width="stretch")

        st.subheader("Theme frequency")
        ex = view.explode("theme_list")
        grp = ex.groupby(["theme_list", "sentiment"]).size().reset_index(name="reviews")
        order = ex["theme_list"].value_counts().index[::-1].tolist()
        st.plotly_chart(px.bar(grp, y="theme_list", x="reviews", color="sentiment", orientation="h",
                               color_discrete_map=COLORS, category_orders={"theme_list": order, "sentiment": SENTIMENTS},
                               labels={"theme_list": ""}), width="stretch")
        other_n = int((ex["theme_list"] == OTHER).sum())
        if other_n:
            st.caption(f"{other_n} review(s) did not fit any theme ({OTHER}).")

        if view["rating"].notna().any():
            st.subheader("Sentiment by star rating")
            rt = view.dropna(subset=["rating"]).assign(rating=lambda d: d["rating"].astype(int))
            g = rt.groupby(["rating", "sentiment"]).size().reset_index(name="reviews")
            st.plotly_chart(px.bar(g, x="rating", y="reviews", color="sentiment", color_discrete_map=COLORS,
                                   category_orders={"sentiment": SENTIMENTS}), width="stretch")
            st.caption("Sentiment is read from the text only. Ratings are shown for comparison, not used to predict it.")

# ------------------------------------------------------------------ feedback table
with tabs[1]:
    q = st.text_input("Search feedback", placeholder="e.g. refund, cold, crashed")
    table = view[view["feedback_text"].str.contains(q, case=False, regex=False)] if q else view
    cols = [c for c in ["review_id", "date", "rating", "order_type", "feedback_text", "sentiment", "themes", "analysis_method"]
            if c in table.columns]
    st.caption(f"{len(table)} review(s)")
    st.dataframe(table[cols], hide_index=True, width="stretch", height=480)

# ------------------------------------------------------------------ insights
with tabs[2]:
    st.caption("Counts come from the data. Every quote below was verified to match its source review exactly. "
               "Insights use all analysed reviews, not the filters above.")
    if not res["points"]:
        st.info("No negative reviews with a theme were found.")
    for i, p in enumerate(res["points"], 1):
        with st.container(border=True):
            st.markdown(f"#### {i}. {p['theme']}")
            st.write(p["summary"])
            st.caption(f"Evidence level: {p['evidence']}")
            for qd in p["quotes"]:
                st.markdown(f"> \"{qd['quote']}\"  \n> *{qd['review_id']}*")
            with st.expander(f"All {p['negative']} negative review IDs"):
                st.write(", ".join(p["review_ids"]))

# ------------------------------------------------------------------ recommendations
with tabs[3]:
    st.caption("Recommendations are hypotheses. Impact and effort are estimates from a simple heuristic "
               "(impact divided by effort), not measured facts or predicted business outcomes.")
    if not res["recs"]:
        st.info("Not enough evidence for a recommendation.")
    else:
        rdf = pd.DataFrame(res["recs"])
        sc = px.scatter(rdf, x="effort_estimate", y="impact_estimate", color="priority", text="theme",
                        color_discrete_map={"High": "#dc2626", "Medium": "#f59e0b", "Low": "#16a34a"},
                        labels={"effort_estimate": "Effort estimate (1 small - 5 large)", "impact_estimate": "Impact estimate (1-5)"})
        sc.update_traces(textposition="top center", marker={"size": 14})
        sc.update_xaxes(range=[0.5, 5.5])
        sc.update_yaxes(range=[0.5, 5.5])
        st.plotly_chart(sc, width="stretch")
        for i, r in enumerate(res["recs"], 1):
            with st.container(border=True):
                st.markdown(f"#### {i}. {r['theme']}  ({r['priority']} priority)")
                st.markdown(f"**Proposed improvement:** {r['recommendation']}")
                st.markdown(f"**Rationale:** {r['rationale']}")
                st.markdown(f"**Expected benefit (hypothesis):** {r['expected_benefit']}")
                st.markdown("**Assumptions:** " + "; ".join(r["assumptions"]))
                m = st.columns(3)
                m[0].metric("Impact (estimate)", r["impact_estimate"])
                m[1].metric("Effort (estimate)", r["effort_estimate"])
                m[2].metric("Score", r["score"])
                st.caption(r["score_note"])
                for qd in r["quotes"]:
                    st.markdown(f"> \"{qd['quote']}\"  \n> *{qd['review_id']}*")
                st.caption(f"Supporting review IDs: {', '.join(r['review_ids'][:15])}"
                           + (" ..." if len(r["review_ids"]) > 15 else "") + f"  |  Text source: {r['text_source']}")

# ------------------------------------------------------------------ evaluation
with tabs[4]:
    st.markdown("Compares predicted sentiment with manual labels on a **separate 20-review synthetic evaluation set**.")
    if not EVAL.exists():
        st.info("sample_data/eval_set_20.csv was not found.")
    else:
        b1, b2 = st.columns(2)
        run_rules = b1.button("Run evaluation (rule-based fallback)")
        run_llm = b2.button("Run evaluation (LLM, sends 20 reviews to Anthropic)", disabled=not (llm_client and use_llm))
        if run_rules or run_llm:
            try:
                res["evaluation"] = evaluate(pd.read_csv(EVAL), client=llm_client if run_llm else None)
            except Exception as e:  # noqa: BLE001 - show a message, never a traceback
                st.error(f"Evaluation failed: {str(e)[:200]}")
        ev = res.get("evaluation")
        if ev:
            e1, e2, e3 = st.columns(3)
            e1.metric("Sentiment accuracy", f"{ev['accuracy']:.0%}")
            e2.metric("Correct / total", f"{ev['correct']} / {ev['n']}")
            e3.metric("Test-set size", ev["n"])
            st.caption(f"Method evaluated: {ev['method_label']}")
            cm = px.imshow(ev["confusion"].values, x=SENTIMENTS, y=SENTIMENTS, text_auto=True, color_continuous_scale="Blues",
                           labels={"x": "Predicted", "y": "Manual label", "color": "Reviews"})
            st.plotly_chart(cm, width="stretch")
            pc = pd.DataFrame(ev["per_class"]).T
            for col in ("precision", "recall"):
                pc[col] = pc[col].map(lambda v: "n/a" if v is None else f"{v:.0%}")
            st.dataframe(pc, width="stretch")
            if len(ev["mistakes"]):
                st.markdown("**Misclassified reviews**")
                st.dataframe(ev["mistakes"], hide_index=True, width="stretch")
            for w in ev["warnings"]:
                st.warning(w)
        st.caption("Limitations: only 20 reviews (one mistake = 5 points), synthetic text, and labels written by the project "
                   "author rather than independent annotators. Treat this as a demonstration, not a benchmark.")

# ------------------------------------------------------------------ export
with tabs[5]:
    st.download_button("Download analysed reviews (CSV)", analysed_csv_bytes(df), "feedbackiq_analysed.csv", "text/csv", width="stretch")
    md = report_markdown(df, res["points"], res["recs"], info, res["sample"], res.get("evaluation"))
    st.download_button("Download insights report (Markdown)", md.encode("utf-8"), "feedbackiq_report.md", "text/markdown", width="stretch")
    if res.get("evaluation") is None:
        st.caption("Tip: run the evaluation first to include its results in the report.")
    with st.expander("Preview report"):
        st.markdown(md)

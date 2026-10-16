-- FeedbackIQ product questions, answered in SQL.
-- Run all of them:  python -m fiq.analytics
--
-- Tables (built from the analysed reviews by fiq/analytics.py):
--   reviews(review_id, date 'YYYY-MM-DD', rating 1-5, order_type, sentiment, analysis_method, feedback_text)
--   review_themes(review_id, theme)          one row per review per theme
-- Each query starts with "-- name: <id>" and a "-- question:" line.


-- name: complaint_rate_by_order_type
-- question: Which order types drive complaints?
SELECT order_type,
       COUNT(*)                                                 AS reviews,
       SUM(sentiment = 'Negative')                              AS negative,
       ROUND(100.0 * SUM(sentiment = 'Negative') / COUNT(*), 0) AS negative_pct,
       ROUND(AVG(rating), 2)                                    AS avg_rating
FROM reviews
GROUP BY order_type
ORDER BY negative_pct DESC, order_type;


-- name: top_complaint_themes_by_month
-- question: Is the top complaint a one-off spike or a steady problem?
WITH monthly AS (
    SELECT strftime('%Y-%m', r.date)       AS month,
           t.theme,
           SUM(r.sentiment = 'Negative')   AS negative
    FROM reviews r
    JOIN review_themes t ON t.review_id = r.review_id
    WHERE t.theme <> 'Other / Unclassified'
      AND r.date IS NOT NULL
    GROUP BY month, t.theme
)
SELECT month,
       theme,
       negative,
       RANK() OVER (PARTITION BY month ORDER BY negative DESC) AS rank_in_month
FROM monthly
WHERE negative > 0
ORDER BY month, rank_in_month, theme;


-- name: sentiment_vs_star_rating
-- question: Sentiment is read from text only. Does it agree with the star ratings?
SELECT CASE
           WHEN rating >= 4 THEN '4-5 stars'
           WHEN rating = 3  THEN '3 stars'
           WHEN rating <= 2 THEN '1-2 stars'
           ELSE 'no rating'
       END                                                              AS rating_band,
       COUNT(*)                                                         AS reviews,
       SUM(sentiment = 'Positive')                                      AS positive,
       SUM(sentiment = 'Neutral')                                       AS neutral,
       SUM(sentiment = 'Negative')                                      AS negative,
       SUM((rating >= 4 AND sentiment = 'Negative')
        OR (rating <= 2 AND sentiment = 'Positive'))                    AS contradictions
FROM reviews
GROUP BY rating_band
ORDER BY MIN(COALESCE(rating, 0)) DESC;


-- name: themes_that_fail_together
-- question: Which complaint themes show up together in the same negative review?
SELECT a.theme   AS theme_a,
       b.theme   AS theme_b,
       COUNT(*)  AS negative_reviews
FROM review_themes a
JOIN review_themes b ON b.review_id = a.review_id AND a.theme < b.theme
JOIN reviews r       ON r.review_id = a.review_id
WHERE r.sentiment = 'Negative'
  AND 'Other / Unclassified' NOT IN (a.theme, b.theme)
GROUP BY a.theme, b.theme
HAVING COUNT(*) >= 2
ORDER BY negative_reviews DESC, theme_a, theme_b;

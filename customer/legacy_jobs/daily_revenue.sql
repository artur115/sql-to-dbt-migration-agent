-- job: daily_revenue
-- owner: finance-analytics
-- complexity: simple
-- Gross captured payments per day.

CREATE OR REPLACE TABLE warehouse.legacy_reporting.daily_revenue AS
SELECT paid_ts::DATE AS revenue_date, SUM(amount) AS gross_revenue, COUNT(*) AS payments
FROM warehouse.raw.payments
WHERE amount > 0
GROUP BY 1;

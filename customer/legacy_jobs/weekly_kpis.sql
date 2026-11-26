-- job: weekly_kpis
-- owner: finance-analytics
-- complexity: hard
-- Weekly orders, revenue and sessions; an UPDATE back-fills empty weeks with zero.

CREATE TEMP TABLE tmp_weeks AS
SELECT DISTINCT DATE_TRUNC('week', started_at)::DATE AS week FROM warehouse.raw.web_sessions;

CREATE TEMP TABLE tmp_orders_w AS
SELECT DATE_TRUNC('week', order_ts)::DATE AS week, COUNT(*) AS orders, SUM(net_revenue) AS net_revenue
FROM warehouse.legacy_reporting.order_totals
WHERE status <> 'cancelled'
GROUP BY 1;

CREATE TEMP TABLE tmp_sessions_w AS
SELECT DATE_TRUNC('week', started_at)::DATE AS week, COUNT(*) AS sessions
FROM warehouse.raw.web_sessions GROUP BY 1;

CREATE OR REPLACE TABLE warehouse.legacy_reporting.weekly_kpis AS
SELECT w.week, o.orders, o.net_revenue, s.sessions
FROM tmp_weeks w
LEFT JOIN tmp_orders_w o USING (week)
LEFT JOIN tmp_sessions_w s USING (week);

UPDATE warehouse.legacy_reporting.weekly_kpis SET orders = 0 WHERE orders IS NULL;
UPDATE warehouse.legacy_reporting.weekly_kpis SET net_revenue = 0 WHERE net_revenue IS NULL;

-- job: aov_by_segment
-- owner: finance-analytics
-- complexity: medium
-- Average order value by customer segment and region.

CREATE OR REPLACE TABLE warehouse.legacy_reporting.aov_by_segment AS
SELECT c.segment, c.region, COUNT(*) AS orders, ROUND(AVG(t.gross_amount), 2) AS aov
FROM warehouse.legacy_reporting.order_totals t
JOIN warehouse.raw.customers c ON c.customer_id = t.customer_id
WHERE t.status <> 'cancelled'
GROUP BY 1, 2;

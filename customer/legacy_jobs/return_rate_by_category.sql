-- job: return_rate_by_category
-- owner: ops-analytics
-- complexity: medium
-- Units returned within 60 days over units sold, by category.

CREATE TEMP TABLE tmp_sold AS
SELECT p.category, SUM(i.quantity) AS units_sold
FROM warehouse.raw.order_items i
JOIN warehouse.raw.products p USING (product_id)
GROUP BY 1;

CREATE TEMP TABLE tmp_ret AS
SELECT p.category, SUM(r.quantity) AS units_returned
FROM warehouse.raw.returns r
JOIN warehouse.raw.orders o ON o.order_id = r.order_id AND o._loaded_at = o.order_ts
JOIN warehouse.raw.products p ON p.product_id = r.product_id
WHERE r.return_ts <= o.order_ts + INTERVAL 60 DAY
GROUP BY 1;

CREATE OR REPLACE TABLE warehouse.legacy_reporting.return_rate_by_category AS
SELECT s.category, s.units_sold, COALESCE(r.units_returned, 0) AS units_returned,
       ROUND(COALESCE(r.units_returned, 0) * 1.0 / s.units_sold, 4) AS return_rate
FROM tmp_sold s LEFT JOIN tmp_ret r USING (category);

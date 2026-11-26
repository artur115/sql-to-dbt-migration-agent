-- job: category_monthly_sales
-- owner: merchandising
-- complexity: medium
-- Monthly revenue by category and share of month.

CREATE TEMP TABLE tmp_cat AS
SELECT DATE_TRUNC('month', o.order_ts)::DATE AS month, p.category,
       SUM(i.quantity * i.unit_price) AS revenue
FROM warehouse.raw.order_items i
JOIN warehouse.legacy_reporting.stg_orders_clean o ON o.order_id = i.order_id
JOIN warehouse.raw.products p ON p.product_id = i.product_id
WHERE o.status <> 'cancelled'
GROUP BY 1, 2;

CREATE OR REPLACE TABLE warehouse.legacy_reporting.category_monthly_sales AS
SELECT month, category, revenue,
       ROUND(revenue / SUM(revenue) OVER (PARTITION BY month), 4) AS share_of_month
FROM tmp_cat;

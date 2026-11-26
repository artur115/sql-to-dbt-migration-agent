-- job: promo_usage
-- owner: growth
-- complexity: simple
-- Orders and buyers per promo code.

CREATE OR REPLACE TABLE warehouse.legacy_reporting.promo_usage AS
SELECT COALESCE(promo_code, 'none') AS promo_code,
       COUNT(DISTINCT order_id) AS orders,
       COUNT(DISTINCT customer_id) AS buyers
FROM warehouse.raw.orders
GROUP BY 1;

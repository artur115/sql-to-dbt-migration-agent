-- job: stg_orders_clean
-- owner: data-platform
-- complexity: simple
-- One row per order, latest load wins, status normalised.

CREATE TEMP TABLE tmp_ranked AS
SELECT o.*, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY _loaded_at DESC) AS rn
FROM warehouse.raw.orders o;

CREATE OR REPLACE TABLE warehouse.legacy_reporting.stg_orders_clean AS
SELECT order_id, customer_id, order_ts, LOWER(TRIM(status)) AS status, channel, promo_code
FROM tmp_ranked
WHERE rn = 1;

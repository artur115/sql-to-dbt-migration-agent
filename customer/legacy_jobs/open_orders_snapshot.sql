-- job: open_orders_snapshot
-- owner: ops-analytics
-- complexity: hard
-- Orders shipped in the last 14 days, as of the run date.

CREATE OR REPLACE TABLE warehouse.legacy_reporting.open_orders_snapshot AS
SELECT order_id, customer_id, order_ts, channel
FROM warehouse.legacy_reporting.stg_orders_clean
WHERE status = 'shipped' AND order_ts >= current_date - INTERVAL 14 DAY;

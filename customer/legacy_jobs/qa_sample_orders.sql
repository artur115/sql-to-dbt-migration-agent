-- job: qa_sample_orders
-- owner: data-platform
-- complexity: hard
-- Random 1% sample of orders for manual QA.

CREATE OR REPLACE TABLE warehouse.legacy_reporting.qa_sample_orders AS
SELECT order_id, customer_id, status
FROM warehouse.legacy_reporting.stg_orders_clean
ORDER BY random()
LIMIT 300;

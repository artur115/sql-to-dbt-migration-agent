-- job: customer_status
-- owner: crm-analytics
-- complexity: hard
-- Lifecycle status set by follow-up UPDATE statements.

CREATE OR REPLACE TABLE warehouse.legacy_reporting.customer_status AS
SELECT customer_id, lifetime_orders, lifetime_net_revenue, last_order, 'active' AS status
FROM warehouse.legacy_reporting.customer_orders_summary;

UPDATE warehouse.legacy_reporting.customer_status
SET status = 'prospect' WHERE lifetime_orders = 0;

UPDATE warehouse.legacy_reporting.customer_status
SET status = 'lapsed' WHERE last_order < DATE '2026-05-01';

UPDATE warehouse.legacy_reporting.customer_status
SET status = 'vip' WHERE lifetime_net_revenue >= 2500 AND status = 'active';

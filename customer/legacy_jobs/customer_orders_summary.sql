-- job: customer_orders_summary
-- owner: crm-analytics
-- complexity: medium
-- Lifetime orders and revenue per customer.

CREATE TEMP TABLE tmp_agg AS
SELECT customer_id, COUNT(*) AS lifetime_orders, SUM(net_revenue) AS lifetime_net_revenue,
       MIN(order_ts)::DATE AS first_order, MAX(order_ts)::DATE AS last_order
FROM warehouse.legacy_reporting.order_totals
WHERE status <> 'cancelled' AND customer_id IS NOT NULL
GROUP BY customer_id;

CREATE OR REPLACE TABLE warehouse.legacy_reporting.customer_orders_summary AS
SELECT d.customer_id, d.region, d.segment,
       COALESCE(a.lifetime_orders, 0) AS lifetime_orders,
       COALESCE(a.lifetime_net_revenue, 0) AS lifetime_net_revenue,
       a.first_order, a.last_order
FROM warehouse.legacy_reporting.dim_customers d
LEFT JOIN tmp_agg a ON a.customer_id = d.customer_id;

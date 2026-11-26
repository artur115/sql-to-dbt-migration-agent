-- job: dim_customers
-- owner: crm-analytics
-- complexity: simple
-- Customer attributes plus first order date.

CREATE TEMP TABLE tmp_first AS
SELECT customer_id, MIN(order_ts)::DATE AS first_order_date
FROM warehouse.raw.orders
WHERE customer_id IS NOT NULL
GROUP BY customer_id;

CREATE OR REPLACE TABLE warehouse.legacy_reporting.dim_customers AS
SELECT c.customer_id, c.region, c.segment, c.signup_date, c.marketing_opt_in, f.first_order_date
FROM warehouse.raw.customers c
LEFT JOIN tmp_first f ON f.customer_id = c.customer_id;

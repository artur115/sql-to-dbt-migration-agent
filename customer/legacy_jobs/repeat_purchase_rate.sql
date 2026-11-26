-- job: repeat_purchase_rate
-- owner: crm-analytics
-- complexity: medium
-- Share of new buyers who order again within 30 days, by first-order month.

CREATE TEMP TABLE tmp_seq AS
SELECT customer_id, order_ts,
       LEAD(order_ts) OVER (PARTITION BY customer_id ORDER BY order_ts, order_id) AS next_ts,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_ts, order_id) AS n
FROM warehouse.legacy_reporting.stg_orders_clean
WHERE customer_id IS NOT NULL AND status <> 'cancelled';

-- Legacy quirk kept on purpose: integer division truncates the percentage.
CREATE OR REPLACE TABLE warehouse.legacy_reporting.repeat_purchase_rate AS
SELECT DATE_TRUNC('month', order_ts)::DATE AS cohort_month,
       COUNT(*) AS new_buyers,
       SUM(CASE WHEN next_ts <= order_ts + INTERVAL 30 DAY THEN 1 ELSE 0 END) AS repeat_30d,
       (SUM(CASE WHEN next_ts <= order_ts + INTERVAL 30 DAY THEN 1 ELSE 0 END) * 100) // COUNT(*) AS repeat_pct
FROM tmp_seq
WHERE n = 1
GROUP BY 1;

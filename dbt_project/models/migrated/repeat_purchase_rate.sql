WITH tmp_seq AS (
  SELECT
    customer_id,
    order_ts,
    LEAD(order_ts) OVER (PARTITION BY customer_id ORDER BY order_ts, order_id) AS next_ts,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_ts, order_id) AS n
  FROM {{ ref('stg_orders_clean') }}
  WHERE
    NOT customer_id IS NULL AND status <> 'cancelled'
)
SELECT
  CAST(DATE_TRUNC('MONTH', order_ts) AS DATE) AS cohort_month,
  COUNT(*) AS new_buyers,
  SUM(CASE WHEN next_ts <= order_ts + INTERVAL '30' DAY THEN 1 ELSE 0 END) AS repeat_30d,
  (
    SUM(CASE WHEN next_ts <= order_ts + INTERVAL '30' DAY THEN 1 ELSE 0 END) * 100
  ) // COUNT(*) AS repeat_pct
FROM tmp_seq
WHERE
  n = 1
GROUP BY
  1

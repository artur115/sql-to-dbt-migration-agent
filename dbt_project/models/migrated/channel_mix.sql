WITH tmp_q AS (
  SELECT
    CAST(DATE_TRUNC('QUARTER', order_ts) AS DATE) AS quarter,
    channel,
    COUNT(*) AS orders
  FROM {{ ref('stg_orders_clean') }}
  WHERE
    status <> 'cancelled'
  GROUP BY
    1,
    2
), tmp_q_tot AS (
  SELECT
    quarter,
    SUM(orders) AS total_orders
  FROM tmp_q
  GROUP BY
    quarter
)
SELECT
  q.quarter,
  q.channel,
  q.orders,
  ROUND(q.orders * 1.0 / t.total_orders, 4) AS share
FROM tmp_q AS q
JOIN tmp_q_tot AS t
  USING (quarter)

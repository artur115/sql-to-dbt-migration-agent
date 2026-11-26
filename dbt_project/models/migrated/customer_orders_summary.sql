WITH tmp_agg AS (
  SELECT
    customer_id,
    COUNT(*) AS lifetime_orders,
    SUM(net_revenue) AS lifetime_net_revenue,
    CAST(MIN(order_ts) AS DATE) AS first_order,
    CAST(MAX(order_ts) AS DATE) AS last_order
  FROM {{ ref('order_totals') }}
  WHERE
    status <> 'cancelled' AND NOT customer_id IS NULL
  GROUP BY
    customer_id
)
SELECT
  d.customer_id,
  d.region,
  d.segment,
  COALESCE(a.lifetime_orders, 0) AS lifetime_orders,
  COALESCE(a.lifetime_net_revenue, 0) AS lifetime_net_revenue,
  a.first_order,
  a.last_order
FROM {{ ref('dim_customers') }} AS d
LEFT JOIN tmp_agg AS a
  ON a.customer_id = d.customer_id

SELECT
  c.segment,
  c.region,
  COUNT(*) AS orders,
  ROUND(AVG(t.gross_amount), 2) AS aov
FROM {{ ref('order_totals') }} AS t
JOIN {{ source('raw', 'customers') }} AS c
  ON c.customer_id = t.customer_id
WHERE
  t.status <> 'cancelled'
GROUP BY
  1,
  2

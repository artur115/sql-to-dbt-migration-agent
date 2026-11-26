SELECT
  COALESCE(promo_code, 'none') AS promo_code,
  COUNT(DISTINCT order_id) AS orders,
  COUNT(DISTINCT customer_id) AS buyers
FROM {{ source('raw', 'orders') }}
GROUP BY
  1

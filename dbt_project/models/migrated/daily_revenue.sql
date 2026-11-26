SELECT
  CAST(paid_ts AS DATE) AS revenue_date,
  SUM(amount) AS gross_revenue,
  COUNT(*) AS payments
FROM {{ source('raw', 'payments') }}
WHERE
  amount > 0
GROUP BY
  1

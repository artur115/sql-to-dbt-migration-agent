SELECT
  CAST(paid_ts AS DATE) AS refund_date,
  -SUM(amount) AS refunded,
  COUNT(*) AS refunds
FROM {{ source('raw', 'payments') }}
WHERE
  method = 'refund'
GROUP BY
  1

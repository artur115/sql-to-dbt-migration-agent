SELECT
  CAST(DATE_TRUNC('MONTH', return_ts) AS DATE) AS month,
  reason,
  SUM(quantity) AS units
FROM {{ source('raw', 'returns') }}
GROUP BY
  1,
  2

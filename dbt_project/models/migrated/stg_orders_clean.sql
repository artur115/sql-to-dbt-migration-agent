WITH tmp_ranked AS (
  SELECT
    o.*,
    ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY _loaded_at DESC) AS rn
  FROM {{ source('raw', 'orders') }} AS o
)
SELECT
  order_id,
  customer_id,
  order_ts,
  LOWER(TRIM(status)) AS status,
  channel,
  promo_code
FROM tmp_ranked
WHERE
  rn = 1

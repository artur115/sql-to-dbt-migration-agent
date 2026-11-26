WITH tmp_first AS (
  SELECT
    customer_id,
    CAST(MIN(order_ts) AS DATE) AS first_order_date
  FROM {{ source('raw', 'orders') }}
  WHERE
    NOT customer_id IS NULL
  GROUP BY
    customer_id
)
SELECT
  c.customer_id,
  c.region,
  c.segment,
  c.signup_date,
  c.marketing_opt_in,
  f.first_order_date
FROM {{ source('raw', 'customers') }} AS c
LEFT JOIN tmp_first AS f
  ON f.customer_id = c.customer_id

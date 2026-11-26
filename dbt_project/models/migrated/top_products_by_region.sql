WITH tmp_units AS (
  SELECT
    c.region,
    i.product_id,
    SUM(i.quantity) AS units
  FROM {{ source('raw', 'order_items') }} AS i
  JOIN {{ ref('stg_orders_clean') }} AS o
    ON o.order_id = i.order_id
  JOIN {{ source('raw', 'customers') }} AS c
    ON c.customer_id = o.customer_id
  GROUP BY
    1,
    2
)
SELECT
  region,
  product_id,
  units,
  rnk
FROM (
  SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY region ORDER BY units DESC, product_id) AS rnk
  FROM tmp_units
)
WHERE
  rnk <= 5

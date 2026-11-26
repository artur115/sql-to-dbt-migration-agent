WITH tmp_cat AS (
  SELECT
    CAST(DATE_TRUNC('MONTH', o.order_ts) AS DATE) AS month,
    p.category,
    SUM(i.quantity * i.unit_price) AS revenue
  FROM {{ source('raw', 'order_items') }} AS i
  JOIN {{ ref('stg_orders_clean') }} AS o
    ON o.order_id = i.order_id
  JOIN {{ source('raw', 'products') }} AS p
    ON p.product_id = i.product_id
  WHERE
    o.status <> 'cancelled'
  GROUP BY
    1,
    2
)
SELECT
  month,
  category,
  revenue,
  ROUND(revenue / SUM(revenue) OVER (PARTITION BY month), 4) AS share_of_month
FROM tmp_cat

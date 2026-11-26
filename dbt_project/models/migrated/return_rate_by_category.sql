WITH tmp_sold AS (
  SELECT
    p.category,
    SUM(i.quantity) AS units_sold
  FROM {{ source('raw', 'order_items') }} AS i
  JOIN {{ source('raw', 'products') }} AS p
    USING (product_id)
  GROUP BY
    1
), tmp_ret AS (
  SELECT
    p.category,
    SUM(r.quantity) AS units_returned
  FROM {{ source('raw', 'returns') }} AS r
  JOIN {{ source('raw', 'orders') }} AS o
    ON o.order_id = r.order_id AND o._loaded_at = o.order_ts
  JOIN {{ source('raw', 'products') }} AS p
    ON p.product_id = r.product_id
  WHERE
    r.return_ts <= o.order_ts + INTERVAL '60' DAY
  GROUP BY
    1
)
SELECT
  s.category,
  s.units_sold,
  COALESCE(r.units_returned, 0) AS units_returned,
  ROUND(COALESCE(r.units_returned, 0) * 1.0 / s.units_sold, 4) AS return_rate
FROM tmp_sold AS s
LEFT JOIN tmp_ret AS r
  USING (category)

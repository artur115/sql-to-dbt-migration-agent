WITH audience AS (
  SELECT customer_id, region, segment
  FROM {{ source('raw', 'customers') }}
  WHERE marketing_opt_in
),
damaged_customers AS (
  SELECT o.customer_id
  FROM {{ source('raw', 'returns') }} r
  JOIN {{ source('raw', 'orders') }} o ON o.order_id = r.order_id
  WHERE r.reason = 'damaged' AND o.customer_id IS NOT NULL
)
SELECT a.customer_id, a.region, a.segment
FROM audience a
WHERE NOT EXISTS (
  SELECT 1 FROM damaged_customers d WHERE d.customer_id = a.customer_id
)

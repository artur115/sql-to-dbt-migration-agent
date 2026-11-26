WITH tmp_items AS (
    SELECT order_id,
           SUM(quantity * unit_price) AS gross_amount,
           SUM(quantity) AS units
    FROM {{ source('raw', 'order_items') }}
    GROUP BY order_id
),
tmp_pay AS (
    SELECT order_id,
           SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS captured,
           SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS refunded
    FROM {{ source('raw', 'payments') }}
    GROUP BY order_id
)
SELECT o.order_id,
       o.customer_id,
       o.order_ts,
       o.status,
       o.channel,
       i.gross_amount,
       i.units,
       COALESCE(p.captured, 0) AS captured,
       COALESCE(p.refunded, 0) AS refunded,
       COALESCE(p.captured, 0) - COALESCE(p.refunded, 0) AS net_revenue
FROM {{ ref('stg_orders_clean') }} o
JOIN tmp_items i ON i.order_id = o.order_id
LEFT JOIN tmp_pay p ON p.order_id = o.order_id

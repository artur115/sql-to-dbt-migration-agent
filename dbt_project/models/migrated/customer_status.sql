SELECT
    customer_id,
    lifetime_orders,
    lifetime_net_revenue,
    last_order,
    CASE
        WHEN last_order < DATE '2026-05-01' THEN 'lapsed'
        WHEN lifetime_orders = 0 THEN 'prospect'
        WHEN lifetime_net_revenue >= 2500 THEN 'vip'
        ELSE 'active'
    END AS status
FROM {{ ref('customer_orders_summary') }}

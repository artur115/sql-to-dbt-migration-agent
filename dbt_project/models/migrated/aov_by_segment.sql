SELECT c.segment, c.region, COUNT(*) AS orders, ROUND(AVG(t.gross_amount), 2) AS aov
FROM {{ ref('order_totals') }} t
JOIN {{ source('raw', 'customers') }} c ON c.customer_id = t.customer_id
WHERE t.status <> 'cancelled'
GROUP BY 1, 2

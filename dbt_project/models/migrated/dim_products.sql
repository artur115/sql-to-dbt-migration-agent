SELECT product_id, category, list_price,
       CASE WHEN list_price < 50 THEN 'budget'
            WHEN list_price < 200 THEN 'mid'
            ELSE 'premium' END AS price_band
FROM {{ source('raw', 'products') }}
WHERE is_active

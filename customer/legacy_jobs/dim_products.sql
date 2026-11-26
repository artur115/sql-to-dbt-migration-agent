-- job: dim_products
-- owner: merchandising
-- complexity: simple
-- Active products with a price band.

CREATE OR REPLACE TABLE warehouse.legacy_reporting.dim_products AS
SELECT product_id, category, list_price,
       CASE WHEN list_price < 50 THEN 'budget'
            WHEN list_price < 200 THEN 'mid'
            ELSE 'premium' END AS price_band
FROM warehouse.raw.products
WHERE is_active;

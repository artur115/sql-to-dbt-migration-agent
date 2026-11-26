-- job: top_products_by_region
-- owner: merchandising
-- complexity: medium
-- Top five products by units in each region.

CREATE TEMP TABLE tmp_units AS
SELECT c.region, i.product_id, SUM(i.quantity) AS units
FROM warehouse.raw.order_items i
JOIN warehouse.legacy_reporting.stg_orders_clean o ON o.order_id = i.order_id
JOIN warehouse.raw.customers c ON c.customer_id = o.customer_id
GROUP BY 1, 2;

CREATE OR REPLACE TABLE warehouse.legacy_reporting.top_products_by_region AS
SELECT region, product_id, units, rnk FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY region ORDER BY units DESC, product_id) AS rnk
  FROM tmp_units
) WHERE rnk <= 5;

-- job: marketing_audience
-- owner: growth
-- complexity: hard
-- Opted-in customers, then a DELETE removes anyone with a damaged-item return.

CREATE OR REPLACE TABLE warehouse.legacy_reporting.marketing_audience AS
SELECT customer_id, region, segment
FROM warehouse.raw.customers
WHERE marketing_opt_in;

DELETE FROM warehouse.legacy_reporting.marketing_audience
WHERE customer_id IN (
  SELECT o.customer_id
  FROM warehouse.raw.returns r
  JOIN warehouse.raw.orders o ON o.order_id = r.order_id
  WHERE r.reason = 'damaged' AND o.customer_id IS NOT NULL
);

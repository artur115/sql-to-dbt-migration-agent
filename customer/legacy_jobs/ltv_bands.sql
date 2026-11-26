-- job: ltv_bands
-- owner: crm-analytics
-- complexity: hard
-- Value band per customer set with UPDATE ... FROM against a thresholds table.

CREATE TEMP TABLE tmp_thresholds AS
SELECT segment,
       QUANTILE_CONT(lifetime_net_revenue, 0.5) AS p50,
       QUANTILE_CONT(lifetime_net_revenue, 0.9) AS p90
FROM warehouse.legacy_reporting.customer_orders_summary
WHERE lifetime_orders > 0
GROUP BY segment;

CREATE OR REPLACE TABLE warehouse.legacy_reporting.ltv_bands AS
SELECT customer_id, segment, lifetime_net_revenue, 'low' AS band
FROM warehouse.legacy_reporting.customer_orders_summary
WHERE lifetime_orders > 0;

UPDATE warehouse.legacy_reporting.ltv_bands b
SET band = 'mid'
FROM tmp_thresholds t
WHERE t.segment = b.segment AND b.lifetime_net_revenue >= t.p50;

UPDATE warehouse.legacy_reporting.ltv_bands b
SET band = 'high'
FROM tmp_thresholds t
WHERE t.segment = b.segment AND b.lifetime_net_revenue >= t.p90;

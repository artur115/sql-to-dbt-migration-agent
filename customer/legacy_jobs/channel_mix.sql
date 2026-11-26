-- job: channel_mix
-- owner: growth
-- complexity: medium
-- Order share by channel per quarter.

CREATE TEMP TABLE tmp_q AS
SELECT DATE_TRUNC('quarter', order_ts)::DATE AS quarter, channel, COUNT(*) AS orders
FROM warehouse.legacy_reporting.stg_orders_clean
WHERE status <> 'cancelled'
GROUP BY 1, 2;

CREATE TEMP TABLE tmp_q_tot AS
SELECT quarter, SUM(orders) AS total_orders FROM tmp_q GROUP BY quarter;

CREATE OR REPLACE TABLE warehouse.legacy_reporting.channel_mix AS
SELECT q.quarter, q.channel, q.orders, ROUND(q.orders * 1.0 / t.total_orders, 4) AS share
FROM tmp_q q JOIN tmp_q_tot t USING (quarter);

-- job: session_attribution
-- owner: growth
-- complexity: hard
-- Last web session source within 7 days before each order (correlated subquery).

CREATE OR REPLACE TABLE warehouse.legacy_reporting.session_attribution AS
SELECT o.order_id, o.customer_id, o.order_ts,
       COALESCE((
         SELECT s.source
         FROM warehouse.raw.web_sessions s
         WHERE s.customer_id = o.customer_id
           AND s.started_at <= o.order_ts
           AND s.started_at > o.order_ts - INTERVAL 7 DAY
         ORDER BY s.started_at DESC, s.session_id DESC
         LIMIT 1
       ), 'unattributed') AS last_touch_source
FROM warehouse.legacy_reporting.stg_orders_clean o
WHERE o.customer_id IS NOT NULL AND o.status <> 'cancelled';

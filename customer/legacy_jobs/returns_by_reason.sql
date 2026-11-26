-- job: returns_by_reason
-- owner: ops-analytics
-- complexity: simple
-- Returned units by reason and month.

CREATE OR REPLACE TABLE warehouse.legacy_reporting.returns_by_reason AS
SELECT DATE_TRUNC('month', return_ts)::DATE AS month, reason, SUM(quantity) AS units
FROM warehouse.raw.returns
GROUP BY 1, 2;

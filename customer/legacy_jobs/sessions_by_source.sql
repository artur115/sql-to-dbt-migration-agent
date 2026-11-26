-- job: sessions_by_source
-- owner: growth
-- complexity: simple
-- Monthly sessions and pageviews by traffic source.

CREATE TEMP TABLE tmp_sessions AS
SELECT DATE_TRUNC('month', started_at)::DATE AS month, source, pageviews
FROM warehouse.raw.web_sessions;

CREATE OR REPLACE TABLE warehouse.legacy_reporting.sessions_by_source AS
SELECT month, source, COUNT(*) AS sessions, SUM(pageviews) AS pageviews
FROM tmp_sessions
GROUP BY month, source;

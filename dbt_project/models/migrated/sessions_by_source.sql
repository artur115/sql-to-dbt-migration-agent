WITH tmp_sessions AS (
  SELECT
    CAST(DATE_TRUNC('MONTH', started_at) AS DATE) AS month,
    source,
    pageviews
  FROM {{ source('raw', 'web_sessions') }}
)
SELECT
  month,
  source,
  COUNT(*) AS sessions,
  SUM(pageviews) AS pageviews
FROM tmp_sessions
GROUP BY
  month,
  source

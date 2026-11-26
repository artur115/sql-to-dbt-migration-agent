SELECT
  o.order_id,
  o.customer_id,
  o.order_ts,
  COALESCE(
    (
      SELECT
        s.source
      FROM {{ source('raw', 'web_sessions') }} AS s
      WHERE
        s.customer_id = o.customer_id
        AND s.started_at <= o.order_ts
        AND s.started_at > o.order_ts - INTERVAL '7' DAY
      ORDER BY
        s.started_at DESC,
        s.session_id DESC
      LIMIT 1
    ),
    'unattributed'
  ) AS last_touch_source
FROM {{ ref('stg_orders_clean') }} AS o
WHERE
  NOT o.customer_id IS NULL AND o.status <> 'cancelled'

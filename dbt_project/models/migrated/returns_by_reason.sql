SELECT DATE_TRUNC('month', return_ts)::DATE AS month, reason, SUM(quantity) AS units
FROM {{ source('raw', 'returns') }}
GROUP BY 1, 2

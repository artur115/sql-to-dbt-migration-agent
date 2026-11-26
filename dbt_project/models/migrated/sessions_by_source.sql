with tmp_sessions as (
    select
        cast(date_trunc('month', started_at) as date) as month,
        source,
        pageviews
    from {{ source('raw', 'web_sessions') }}
)

select
    month,
    source,
    count(*) as sessions,
    sum(pageviews) as pageviews
from tmp_sessions
group by month, source

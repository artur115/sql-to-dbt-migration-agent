with tmp_weeks as (
    select distinct date_trunc('week', started_at)::date as week
    from {{ source('raw', 'web_sessions') }}
),
tmp_orders_w as (
    select date_trunc('week', order_ts)::date as week, count(*) as orders, sum(net_revenue) as net_revenue
    from {{ ref('order_totals') }}
    where status <> 'cancelled'
    group by 1
),
tmp_sessions_w as (
    select date_trunc('week', started_at)::date as week, count(*) as sessions
    from {{ source('raw', 'web_sessions') }}
    group by 1
)
select
    w.week,
    case when o.orders is null then 0 else o.orders end as orders,
    case when o.net_revenue is null then 0 else o.net_revenue end as net_revenue,
    s.sessions
from tmp_weeks w
left join tmp_orders_w o using (week)
left join tmp_sessions_w s using (week)

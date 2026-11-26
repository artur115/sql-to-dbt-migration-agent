with base as (
    select d.revenue_date as day,
           d.gross_revenue,
           coalesce(r.refunded, 0) as refunded,
           d.gross_revenue - coalesce(r.refunded, 0) as net_revenue
    from {{ ref('daily_revenue') }} d
    left join {{ ref('refunds_daily') }} r on r.refund_date = d.revenue_date
),
refund_only as (
    select r.refund_date as day,
           0 as gross_revenue,
           r.refunded as refunded,
           -r.refunded as net_revenue
    from {{ ref('refunds_daily') }} r
    where r.refund_date not in (select revenue_date from {{ ref('daily_revenue') }})
)
select day, gross_revenue, refunded, net_revenue from base
union all
select day, gross_revenue, refunded, net_revenue from refund_only

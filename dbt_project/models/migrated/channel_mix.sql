with tmp_q as (
    select
        date_trunc('quarter', order_ts)::date as quarter,
        channel,
        count(*) as orders
    from {{ ref('stg_orders_clean') }}
    where status <> 'cancelled'
    group by 1, 2
),

tmp_q_tot as (
    select
        quarter,
        sum(orders) as total_orders
    from tmp_q
    group by quarter
)

select
    q.quarter,
    q.channel,
    q.orders,
    round(q.orders * 1.0 / t.total_orders, 4) as share
from tmp_q q
join tmp_q_tot t using (quarter)

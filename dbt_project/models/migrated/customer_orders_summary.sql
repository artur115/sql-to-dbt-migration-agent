with tmp_agg as (
    select
        customer_id,
        count(*) as lifetime_orders,
        sum(net_revenue) as lifetime_net_revenue,
        min(order_ts)::date as first_order,
        max(order_ts)::date as last_order
    from {{ ref('order_totals') }}
    where status <> 'cancelled' and customer_id is not null
    group by customer_id
)
select
    d.customer_id,
    d.region,
    d.segment,
    coalesce(a.lifetime_orders, 0) as lifetime_orders,
    coalesce(a.lifetime_net_revenue, 0) as lifetime_net_revenue,
    a.first_order,
    a.last_order
from {{ ref('dim_customers') }} d
left join tmp_agg a on a.customer_id = d.customer_id

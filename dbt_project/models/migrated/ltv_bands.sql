with thresholds as (
    select segment,
           quantile_cont(lifetime_net_revenue, 0.5) as p50,
           quantile_cont(lifetime_net_revenue, 0.9) as p90
    from {{ ref('customer_orders_summary') }}
    where lifetime_orders > 0
    group by segment
),
base as (
    select customer_id, segment, lifetime_net_revenue, 'low' as band
    from {{ ref('customer_orders_summary') }}
    where lifetime_orders > 0
)
select b.customer_id,
       b.segment,
       b.lifetime_net_revenue,
       case
           when b.lifetime_net_revenue >= t.p90 then 'high'
           when b.lifetime_net_revenue >= t.p50 then 'mid'
           else b.band
       end as band
from base b
left join thresholds t
  on t.segment = b.segment

with tmp_cat as (
    select
        date_trunc('month', o.order_ts)::date as month,
        p.category,
        sum(i.quantity * i.unit_price) as revenue
    from {{ source('raw', 'order_items') }} i
    join {{ ref('stg_orders_clean') }} o on o.order_id = i.order_id
    join {{ source('raw', 'products') }} p on p.product_id = i.product_id
    where o.status <> 'cancelled'
    group by 1, 2
)
select
    month,
    category,
    revenue,
    round(revenue / sum(revenue) over (partition by month), 4) as share_of_month
from tmp_cat

with tmp_first as (
    select
        customer_id,
        min(order_ts)::date as first_order_date
    from {{ source('raw', 'orders') }}
    where customer_id is not null
    group by customer_id
)

select
    c.customer_id,
    c.region,
    c.segment,
    c.signup_date,
    c.marketing_opt_in,
    f.first_order_date
from {{ source('raw', 'customers') }} c
left join tmp_first f
    on f.customer_id = c.customer_id

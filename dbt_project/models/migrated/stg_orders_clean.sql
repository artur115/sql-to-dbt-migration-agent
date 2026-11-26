with tmp_ranked as (
    select
        o.*,
        row_number() over (
            partition by order_id
            order by _loaded_at desc nulls first
        ) as rn
    from {{ source('raw', 'orders') }} o
)
select
    order_id,
    customer_id,
    order_ts,
    lower(trim(status)) as status,
    channel,
    promo_code
from tmp_ranked
where rn = 1

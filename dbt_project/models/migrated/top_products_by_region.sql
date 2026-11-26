with tmp_units as (
  select c.region, i.product_id, sum(i.quantity) as units
  from {{ source('raw', 'order_items') }} i
  join {{ ref('stg_orders_clean') }} o on o.order_id = i.order_id
  join {{ source('raw', 'customers') }} c on c.customer_id = o.customer_id
  group by 1, 2
)
select region, product_id, units, rnk from (
  select *, row_number() over (partition by region order by units desc, product_id) as rnk
  from tmp_units
) ranked
where rnk <= 5

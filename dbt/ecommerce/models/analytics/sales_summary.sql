with sales as (

    select *
    from {{ ref('fct_sales') }}

)

select
    count(*) as total_records,

    count(distinct order_id) as total_orders,

    coalesce(
        sum(quantity),
        0
    ) as total_quantity,

    coalesce(
        sum(amount),
        0
    )::numeric(18, 2) as total_sales,

    coalesce(
        avg(amount),
        0
    )::numeric(18, 2) as average_line_amount

from sales
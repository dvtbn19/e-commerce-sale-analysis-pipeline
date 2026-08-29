with sales as (

    select *
    from {{ ref('fct_sales') }}

)

select
    category,

    count(*) as total_records,

    coalesce(
        sum(quantity),
        0
    ) as total_quantity,

    coalesce(
        sum(amount),
        0
    )::numeric(18, 2) as total_sales

from sales

where category is not null

group by category
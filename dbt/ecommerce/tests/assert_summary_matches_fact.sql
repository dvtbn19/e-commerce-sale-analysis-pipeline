with fact_metrics as (

    select
        count(*) as total_records,
        count(distinct order_id) as total_orders,
        sum(quantity) as total_quantity,
        sum(amount)::numeric(18, 2) as total_sales

    from {{ ref('fct_sales') }}

),

summary as (

    select
        total_records,
        total_orders,
        total_quantity,
        total_sales

    from {{ ref('sales_summary') }}

)

select
    summary.*

from summary
cross join fact_metrics

where
       summary.total_records != fact_metrics.total_records
    or summary.total_orders != fact_metrics.total_orders
    or summary.total_quantity != fact_metrics.total_quantity
    or summary.total_sales != fact_metrics.total_sales
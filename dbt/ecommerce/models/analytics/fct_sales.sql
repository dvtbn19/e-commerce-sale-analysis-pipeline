with sales as (

    select *
    from {{ ref('stg_amazon_sales') }}

)

select
    source_row_id,
    order_id,
    order_date,
    status,
    fulfilment,
    sales_channel,
    ship_service_level,
    style,
    sku,
    category,
    size,
    asin,
    courier_status,
    quantity,
    currency,
    amount,
    ship_city,
    ship_state,
    ship_postal_code,
    ship_country,
    promotion_ids,
    is_b2b,
    fulfilled_by
from sales
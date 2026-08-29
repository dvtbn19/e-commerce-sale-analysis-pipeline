with source as (

    select *
    from {{ source('ecommerce_raw', 'amazon_sales') }}

),

cleaned as (

    select

        "index"::bigint as source_row_id,

        nullif(trim(order_id), '') as order_id,

        to_date(
            nullif(trim(date), ''),
            'MM-DD-YY'
        ) as order_date,

        nullif(trim(status), '') as status,

        nullif(trim(fulfilment), '') as fulfilment,

        nullif(trim(sales_channel), '') as sales_channel,

        nullif(trim(ship_service_level), '') as ship_service_level,

        nullif(trim(style), '') as style,

        nullif(trim(sku), '') as sku,

        initcap(
            nullif(trim(category), '')
        ) as category,

        nullif(trim(size), '') as size,

        nullif(trim(asin), '') as asin,

        nullif(trim(courier_status), '') as courier_status,

        qty::integer as quantity,

        nullif(trim(currency), '') as currency,

        amount::numeric(18, 2) as amount,

        nullif(trim(ship_city), '') as ship_city,

        nullif(trim(ship_state), '') as ship_state,

        case
            when ship_postal_code is null then null
            else ship_postal_code::bigint::text
        end as ship_postal_code,

        nullif(trim(ship_country), '') as ship_country,

        nullif(trim(promotion_ids), '') as promotion_ids,

        b2b::boolean as is_b2b,

        nullif(trim(fulfilled_by), '') as fulfilled_by

    from source

)

select *
from cleaned
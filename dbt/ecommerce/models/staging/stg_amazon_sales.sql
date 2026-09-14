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

),

-- Sales entered through the API live in their own raw table, so that the CSV
-- load can truncate and reload raw.amazon_sales without destroying them. They
-- are typed correctly at rest, so they need casting and trimming only where
-- the shapes genuinely differ. Columns the form does not collect are filled
-- with NULL to line the two sources up.
manual as (

    select

        id as source_row_id,

        order_id,

        order_date,

        status,

        fulfilment,

        sales_channel,

        null::text as ship_service_level,

        null::text as style,

        null::text as sku,

        initcap(
            nullif(trim(category), '')
        ) as category,

        null::text as size,

        null::text as asin,

        null::text as courier_status,

        quantity,

        nullif(trim(currency), '') as currency,

        amount,

        nullif(trim(ship_city), '') as ship_city,

        nullif(trim(ship_state), '') as ship_state,

        null::text as ship_postal_code,

        null::text as ship_country,

        null::text as promotion_ids,

        is_b2b,

        null::text as fulfilled_by

    from {{ source('ecommerce_raw', 'manual_sales') }}

)

select *
from cleaned

union all

select *
from manual
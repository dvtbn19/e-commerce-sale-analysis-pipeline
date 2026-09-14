-- The staging model unions the CSV dump with sales entered through the API,
-- so "the raw row count" is the sum of both raw tables, not just the CSV one.
with raw_count as (

    select
        (select count(*) from {{ source('ecommerce_raw', 'amazon_sales') }})
        +
        (select count(*) from {{ source('ecommerce_raw', 'manual_sales') }})
        as row_count

),

staging_count as (

    select count(*) as row_count
    from {{ ref('stg_amazon_sales') }}

)

select
    raw_count.row_count as raw_rows,
    staging_count.row_count as staging_rows

from raw_count
cross join staging_count

where raw_count.row_count != staging_count.row_count
-- raw.amazon_sales.date is a text column carrying the source CSV's MM-DD-YY
-- format, and stg_amazon_sales parses it with exactly that mask. A row written
-- in any other format (an ISO date from the API's write endpoint, for example)
-- does not fail on insert -- it makes the next `dbt run` fail while building
-- fct_sales, long after the row looked accepted.
--
-- This test moves that failure earlier: `dbt test` reports the offending rows
-- by name instead of `dbt run` dying on a type error.

select
    "index" as source_row_id,
    order_id,
    date as unparseable_date

from {{ source('ecommerce_raw', 'amazon_sales') }}

where nullif(trim(date), '') is not null
  and trim(date) !~ '^\d{2}-\d{2}-\d{2}$'

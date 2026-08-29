import math

from fastapi import APIRouter, Query, Response
from sqlalchemy import text

from app.db.database import engine
from app.cache.cache_service import (
    get_cached_json,
    set_cached_json,
)
from app.core.config import REDIS_TTL_SECONDS


router = APIRouter(
    prefix="/api/sales",
    tags=["sales"],
)

SUMMARY_CACHE_KEY = "ecommerce:sales:summary:v1"
CATEGORIES_CACHE_KEY = "ecommerce:sales:categories:v1"
SALES_CACHE_PREFIX = "ecommerce:sales:list:v1"


def build_sales_cache_key(
    page: int,
    page_size: int,
) -> str:
    return (
        f"{SALES_CACHE_PREFIX}"
        f":page:{page}"
        f":size:{page_size}"
    )

@router.get("")
def get_sales(
    response: Response,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
):
    cache_key = build_sales_cache_key(
        page=page,
        page_size=page_size,
    )

    cached_data = get_cached_json(cache_key)

    if cached_data is not None:
        response.headers["X-Cache"] = "HIT"
        return cached_data

    offset = (page - 1) * page_size

    with engine.connect() as connection:

        total = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM analytics.fct_sales
                """
            )
        ).scalar()

        result = connection.execute(
            text(
                """
                SELECT
                    source_row_id AS index,
                    order_id,
                    order_date AS date,
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
                    quantity AS qty,
                    currency,
                    amount,
                    ship_city,
                    ship_state,
                    ship_postal_code,
                    ship_country,
                    promotion_ids,
                    is_b2b AS b2b,
                    fulfilled_by
                FROM analytics.fct_sales
                ORDER BY source_row_id
                LIMIT :limit
                OFFSET :offset
                """
            ),
            {
                "limit": page_size,
                "offset": offset,
            },
        )

        rows = result.mappings().all()

    payload = {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": math.ceil(total / page_size),
        "data": [dict(row) for row in rows],
    }

    cache_written = set_cached_json(
        cache_key,
        payload,
        REDIS_TTL_SECONDS,
    )

    response.headers["X-Cache"] = (
        "MISS" if cache_written else "BYPASS"
    )

    return payload

@router.get("/summary")
def get_sales_summary(response: Response):

    cached_data = get_cached_json(SUMMARY_CACHE_KEY)

    if cached_data is not None:
        response.headers["X-Cache"] = "HIT"
        return cached_data

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT
                    total_records,
                    total_orders,
                    total_quantity,
                    total_sales,
                    average_line_amount
                FROM analytics.sales_summary
                """
            )
        )

        row = result.mappings().one()

    payload = dict(row)

    cache_written = set_cached_json(
        SUMMARY_CACHE_KEY,
        payload,
        REDIS_TTL_SECONDS,
    )

    response.headers["X-Cache"] = (
        "MISS" if cache_written else "BYPASS"
    )

    return payload


@router.get("/categories")
def get_sales_by_category(response: Response):

    cached_data = get_cached_json(CATEGORIES_CACHE_KEY)

    if cached_data is not None:
        response.headers["X-Cache"] = "HIT"
        return cached_data

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT
                    category,
                    total_records,
                    total_quantity,
                    total_sales
                FROM analytics.sales_by_category
                ORDER BY total_sales DESC
                """
            )
        )

        rows = result.mappings().all()

    payload = {
        "data": [dict(row) for row in rows]
    }

    cache_written = set_cached_json(
        CATEGORIES_CACHE_KEY,
        payload,
        REDIS_TTL_SECONDS,
    )

    response.headers["X-Cache"] = (
        "MISS" if cache_written else "BYPASS"
    )

    return payload

@router.get("/summary/raw")
def get_sales_summary_raw():

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT
                    total_records,
                    total_orders,
                    total_quantity,
                    total_sales,
                    average_line_amount
                FROM analytics.sales_summary
                """
            )
        )

        row = result.mappings().one()

    return dict(row)
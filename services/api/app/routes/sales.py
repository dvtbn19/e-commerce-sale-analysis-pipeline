import math

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text

from app.db.database import engine
from app.cache.cache_service import (
    get_cached_json,
    set_cached_json,
)
from app.core.config import REDIS_TTL_SECONDS
import uuid
from datetime import date as date_type
from enum import Enum

from fastapi import Depends
from pydantic import BaseModel, Field
from redis.exceptions import RedisError

from app.auth.security import get_current_user
from app.cache.cache_service import invalidate_sales_cache
from app.cache.redis_client import redis_client


class SaleCategory(str, Enum):
    SET = "Set"
    KURTA = "Kurta"
    WESTERN_DRESS = "Western Dress"
    TOP = "Top"
    ETHNIC_DRESS = "Ethnic Dress"
    BLOUSE = "Blouse"
    BOTTOM = "Bottom"
    SAREE = "Saree"
    DUPATTA = "Dupatta"


class NewSaleRequest(BaseModel):
    category: SaleCategory
    quantity: int = Field(gt=0, le=1000)
    amount: float = Field(gt=0, le=10_000_000)
    ship_city: str | None = Field(default=None, max_length=128)
    ship_state: str | None = Field(default=None, max_length=128)


RATE_LIMIT_MAX_REQUESTS = 20
RATE_LIMIT_WINDOW_SECONDS = 60


def _check_rate_limit(username: str) -> None:
    key = f"ecommerce:ratelimit:create_sale:{username}"

    try:
        current = redis_client.incr(key)

        if current == 1:
            redis_client.expire(key, RATE_LIMIT_WINDOW_SECONDS)

        if current > RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please slow down.",
            )

    except RedisError:
        pass



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
                ORDER BY source_row_id DESC
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

@router.post("", status_code=201)
def create_sale(
    payload: NewSaleRequest,
    current_user: str = Depends(get_current_user),
):
    _check_rate_limit(current_user)

    today = date_type.today()

    row = {
        "order_id": f"MANUAL-{uuid.uuid4().hex[:12].upper()}",
        "order_date": today,
        "status": "Manual Entry",
        "fulfilment": "Merchant",
        "sales_channel": "Website",
        "category": payload.category.value,
        "quantity": payload.quantity,
        "currency": "INR",
        "amount": payload.amount,
        "ship_city": payload.ship_city,
        "ship_state": payload.ship_state,
        "is_b2b": False,
        "created_by": current_user,
    }

    with engine.begin() as connection:
        # Writes go to raw.manual_sales, never to raw.amazon_sales: the CSV
        # loader truncates and reloads its own table on every pipeline run, so
        # a row written there would be destroyed the next time Airflow runs.
        # The staging model unions the two, which is where they converge.
        result = connection.execute(
            text(
                """
                INSERT INTO raw.manual_sales (
                    order_id, order_date, status, fulfilment, sales_channel,
                    category, quantity, currency, amount, ship_city,
                    ship_state, is_b2b, created_by
                )
                VALUES (
                    :order_id, :order_date, :status, :fulfilment,
                    :sales_channel, :category, :quantity, :currency, :amount,
                    :ship_city, :ship_state, :is_b2b, :created_by
                )
                RETURNING id
                """
            ),
            row,
        )
        source_row_id = result.scalar_one()

        # The same row is written straight into the fact table as well, so the
        # dashboard reflects it immediately instead of at the next dbt run.
        # Columns the form does not collect are left to default to NULL, which
        # is exactly what the staging model produces for them.
        connection.execute(
            text(
                """
                INSERT INTO analytics.fct_sales (
                    source_row_id, order_id, order_date, status, fulfilment,
                    sales_channel, category, quantity, currency, amount,
                    ship_city, ship_state, is_b2b
                )
                VALUES (
                    :source_row_id, :order_id, :order_date, :status,
                    :fulfilment, :sales_channel, :category, :quantity,
                    :currency, :amount, :ship_city, :ship_state, :is_b2b
                )
                """
            ),
            {**row, "source_row_id": source_row_id},
        )

        connection.execute(text("TRUNCATE analytics.sales_summary;"))
        connection.execute(
            text(
                """
                INSERT INTO analytics.sales_summary (
                    total_records, total_orders, total_quantity,
                    total_sales, average_line_amount
                )
                SELECT
                    count(*),
                    count(distinct order_id),
                    coalesce(sum(quantity), 0),
                    coalesce(sum(amount), 0)::numeric(18, 2),
                    coalesce(avg(amount), 0)::numeric(18, 2)
                FROM analytics.fct_sales;
                """
            )
        )

        connection.execute(text("TRUNCATE analytics.sales_by_category;"))
        connection.execute(
            text(
                """
                INSERT INTO analytics.sales_by_category (
                    category, total_records, total_quantity, total_sales
                )
                SELECT
                    category,
                    count(*),
                    coalesce(sum(quantity), 0),
                    coalesce(sum(amount), 0)::numeric(18, 2)
                FROM analytics.fct_sales
                GROUP BY category
                ORDER BY sum(amount) DESC;
                """
            )
        )

    invalidate_sales_cache()

    return {
        "source_row_id": source_row_id,
        "order_id": row["order_id"],
        **payload.model_dump(),
    }

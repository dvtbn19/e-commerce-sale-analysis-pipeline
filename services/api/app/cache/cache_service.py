import json
import logging
from typing import Any

from fastapi.encoders import jsonable_encoder
from redis.exceptions import RedisError

from app.cache.redis_client import redis_client


logger = logging.getLogger(__name__)


def get_cached_json(key: str) -> Any | None:
    try:
        cached_value = redis_client.get(key)

        if cached_value is None:
            return None

        return json.loads(cached_value)

    except (RedisError, json.JSONDecodeError) as exc:
        logger.warning(
            "Redis GET failed for key %s: %s",
            key,
            exc,
        )

        return None


def set_cached_json(
    key: str,
    value: Any,
    ttl_seconds: int,
) -> bool:
    try:
        encoded_value = jsonable_encoder(value)

        redis_client.setex(
            key,
            ttl_seconds,
            json.dumps(encoded_value),
        )

        return True

    except RedisError as exc:
        logger.warning(
            "Redis SET failed for key %s: %s",
            key,
            exc,
        )

        return False

SALES_CACHE_KEYS_TO_CLEAR = (
    "ecommerce:sales:summary:v1",
    "ecommerce:sales:categories:v1",
)
SALES_LIST_CACHE_PREFIX = "ecommerce:sales:list:v1:*"


def invalidate_sales_cache() -> None:
    try:
        keys_to_delete = list(SALES_CACHE_KEYS_TO_CLEAR)

        for key in redis_client.scan_iter(
            match=SALES_LIST_CACHE_PREFIX,
            count=100,
        ):
            keys_to_delete.append(key)

        if keys_to_delete:
            redis_client.delete(*keys_to_delete)

    except RedisError as exc:
        logger.warning("Cache invalidation failed: %s", exc)

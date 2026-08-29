import redis

from app.core.config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
)


redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)
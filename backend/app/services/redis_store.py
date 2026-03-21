from __future__ import annotations

import json
import logging
import time
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Redis | None = None
_client_failed = False


def get_redis_client() -> Redis | None:
    global _client, _client_failed
    if _client is not None:
        return _client
    if _client_failed or not settings.REDIS_URL.strip():
        return None

    try:
        client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        _client = client
        return _client
    except RedisError as exc:
        logger.warning("Redis unavailable, falling back to in-process storage: %s", exc)
        _client_failed = True
        return None


def redis_health() -> dict[str, Any]:
    client = get_redis_client()
    if client is None:
        return {"configured": bool(settings.REDIS_URL.strip()), "connected": False}
    try:
        pong = client.ping()
        return {"configured": True, "connected": bool(pong)}
    except RedisError:
        return {"configured": True, "connected": False}


def get_json(key: str) -> Any | None:
    client = get_redis_client()
    if client is None:
        return None
    try:
        payload = client.get(key)
    except RedisError:
        return None
    if payload is None:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def set_json(key: str, value: Any, ttl_seconds: int) -> bool:
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.setex(key, ttl_seconds, json.dumps(value))
        return True
    except (RedisError, TypeError):
        return False


def sliding_window_allow(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    client = get_redis_client()
    if client is None:
        return True, 0

    now = time.time()
    cutoff = now - window_seconds
    try:
        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, cutoff)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds)
        _, count, _, _ = pipe.execute()
    except RedisError:
        return True, 0

    if int(count) >= limit:
        retry_after = max(1, window_seconds)
        return False, retry_after
    return True, 0

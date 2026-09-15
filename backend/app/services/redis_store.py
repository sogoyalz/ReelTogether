from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Redis | None = None
_retry_at = 0.0


def get_redis_client() -> Redis | None:
    global _client, _retry_at
    if _client is not None:
        return _client
    if time.monotonic() < _retry_at or not settings.REDIS_URL.strip():
        return None

    try:
        client = Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=0.5, socket_connect_timeout=0.5)
        client.ping()
        _client = client
        return _client
    except RedisError as exc:
        logger.warning("Redis unavailable, falling back to in-process storage: %s", exc)
        _retry_at = time.monotonic() + 30
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
    script = """
    redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1])
    if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then return 0 end
    redis.call('ZADD', KEYS[1], ARGV[3], ARGV[4])
    redis.call('EXPIRE', KEYS[1], ARGV[5])
    return 1
    """
    try:
        allowed = bool(client.eval(script, 1, key, now - window_seconds, limit, now, str(uuid.uuid4()), window_seconds))
    except RedisError:
        return True, 0
    return allowed, 0 if allowed else window_seconds

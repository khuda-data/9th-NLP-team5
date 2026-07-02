import json
import os
from logger import get_logger

logger = get_logger(__name__)

_TTL = int(os.getenv("CACHE_TTL", 3600))

try:
    import redis as _redis_lib
    _redis = _redis_lib.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True,
        socket_connect_timeout=1,
    )
    _redis.ping()
    _backend = "redis"
    logger.info("cache | backend=redis host=%s", os.getenv("REDIS_HOST", "localhost"))
except Exception:
    _redis = None
    _backend = "memory"
    logger.info("cache | backend=memory (redis connection failed)")

_mem: dict = {}


def get(key: str):
    if _backend == "redis":
        val = _redis.get(key)
        return json.loads(val) if val else None
    return _mem.get(key)


def set(key: str, value: dict, ttl: int = _TTL):
    if _backend == "redis":
        _redis.setex(key, ttl, json.dumps(value, ensure_ascii=False))
    else:
        _mem[key] = value


def make_music_key(scale: str, mood_keywords: list[str]) -> str:
    keywords = ",".join(sorted(mood_keywords))
    return f"music:{scale.replace(' ', '_')}:{keywords}"

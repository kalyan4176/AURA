import json
from typing import Optional
from redis import Redis
from loguru import logger

from app.core.config import settings


class RedisCache:
    """Enterprise Redis Caching abstraction with local/in-memory fallback."""

    def __init__(self):
        try:
            self.client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.client.ping()
            self.active = True
            logger.info("Successfully connected to Redis Cache.")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis. Caching will fall back to in-memory dictionary. Error: {e}")
            self.client = {}
            self.active = False

    def get(self, key: str) -> Optional[str]:
        try:
            if self.active:
                return self.client.get(key)
            else:
                return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis cache GET failed: {e}")
            return None

    def set(self, key: str, value: str, expire_seconds: int = 3600) -> bool:
        try:
            if self.active:
                self.client.set(key, value, ex=expire_seconds)
            else:
                self.client[key] = value
            return True
        except Exception as e:
            logger.error(f"Redis cache SET failed: {e}")
            return False

    def get_json(self, key: str) -> Optional[dict]:
        val = self.get(key)
        if not val:
            return None
        try:
            return json.loads(val)
        except Exception as e:
            logger.error(f"Failed parsing JSON cache entry for {key}: {e}")
            return None

    def set_json(self, key: str, value: dict, expire_seconds: int = 3600) -> bool:
        try:
            return self.set(key, json.dumps(value), expire_seconds)
        except Exception as e:
            logger.error(f"Failed serializing JSON cache entry: {e}")
            return False


redis_cache = RedisCache()

"""
Redis cache service: customer profiles, network status, sessions, pub/sub.
"""

import json
from typing import Any, AsyncGenerator, Optional, List

import redis.asyncio as aioredis
from loguru import logger

from config.settings import settings


class CacheService:
    def __init__(self) -> None:
        self._client: Optional[aioredis.Redis] = None

    @property
    def client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()

    # ── Generic ────────────────────────────────────────────────────────
    async def get(self, key: str) -> Optional[dict]:
        raw = await self.client.get(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        await self.client.set(key, json.dumps(value, default=str), ex=ttl)

    async def delete(self, *keys: str) -> int:
        if not keys:
            return 0
        return await self.client.delete(*keys)

    # ── Customer Profile Cache ────────────────────────────────────────
    async def get_customer_profile(self, customer_id: str) -> Optional[dict]:
        return await self.get(f"customer:profile:{customer_id}")

    async def set_customer_profile(self, customer_id: str, profile: dict,
                                    ttl: int = None) -> None:
        await self.set(
            f"customer:profile:{customer_id}", profile,
            ttl=ttl or settings.redis_cache_ttl,
        )

    async def invalidate_customer(self, customer_id: str) -> None:
        await self.delete(
            f"customer:profile:{customer_id}",
            f"customer:by_phone:*",  # caller should also clear phone lookups
        )

    # ── Network Status Cache ──────────────────────────────────────────
    async def get_network_status(self, area_id: str) -> Optional[dict]:
        return await self.get(f"network:area:{area_id}")

    async def set_network_status(self, area_id: str, status: dict,
                                  ttl: int = None) -> None:
        await self.set(
            f"network:area:{area_id}", status,
            ttl=ttl or settings.redis_network_ttl,
        )

    async def get_device_status(self, device_id: str) -> Optional[dict]:
        return await self.get(f"network:device:{device_id}")

    async def set_device_status(self, device_id: str, status: dict,
                                 ttl: int = None) -> None:
        await self.set(
            f"network:device:{device_id}", status,
            ttl=ttl or settings.redis_network_ttl,
        )

    # ── Voice Session State (replaces in-memory conversation store) ────
    async def get_session(self, session_id: str) -> Optional[dict]:
        return await self.get(f"session:{session_id}")

    async def set_session(self, session_id: str, data: dict,
                          ttl: int = None) -> None:
        await self.set(
            f"session:{session_id}", data,
            ttl=ttl or settings.redis_session_ttl,
        )

    async def delete_session(self, session_id: str) -> None:
        await self.delete(f"session:{session_id}")

    # ── Pub/Sub (real-time dashboard events) ──────────────────────────
    async def publish_call_event(self, event_type: str, data: dict) -> None:
        await self.client.publish(
            f"calls:{event_type}",
            json.dumps(data, default=str),
        )

    async def publish_ticket_event(self, event_type: str, data: dict) -> None:
        await self.client.publish(
            f"tickets:{event_type}",
            json.dumps(data, default=str),
        )

    async def publish_network_event(self, event_type: str, data: dict) -> None:
        await self.client.publish(
            f"network:{event_type}",
            json.dumps(data, default=str),
        )

    async def subscribe(self, channels: List[str]) -> AsyncGenerator[dict, None]:
        pubsub = self.client.pubsub()
        await pubsub.subscribe(*channels)
        try:
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    try:
                        yield {
                            "channel": message["channel"],
                            "data": json.loads(message["data"]),
                        }
                    except Exception as e:
                        logger.warning(f"Pub/sub decode error: {e}")
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()

    # ── Rate-limit counters / OTP storage ─────────────────────────────
    async def incr_counter(self, key: str, window_seconds: int) -> int:
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        results = await pipe.execute()
        return int(results[0])

    async def store_otp(self, key: str, otp: str, ttl: int = 300) -> None:
        await self.client.set(f"otp:{key}", otp, ex=ttl)

    async def verify_otp_stored(self, key: str, otp: str) -> bool:
        stored = await self.client.get(f"otp:{key}")
        if not stored:
            return False
        if stored == otp:
            await self.client.delete(f"otp:{key}")
            return True
        return False


cache_service = CacheService()

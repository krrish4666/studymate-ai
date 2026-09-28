import hashlib
import json
import logging
from collections.abc import Mapping
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class ArtifactCache:
    """Best-effort Redis cache for validated AI artifact payloads."""

    KEY_PREFIX = "studymate:artifact"
    CACHE_VERSION = "v1"

    def __init__(self) -> None:
        self._client: Any = None

    @property
    def enabled(self) -> bool:
        return settings.REDIS_ENABLED

    def build_key(
        self,
        user_id: Any,
        file_record_id: Any,
        artifact_type: str,
        parameters: Mapping[str, Any] | None = None,
        source_context: str | None = None,
        model: str | None = None,
    ) -> str:
        identity = {
            "artifact": artifact_type,
            "model": model or "",
            "parameters": dict(parameters or {}),
            "source_context": source_context or "",
            "version": self.CACHE_VERSION,
        }
        digest = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        return f"{self.KEY_PREFIX}:{user_id}:{file_record_id}:{artifact_type}:{self.CACHE_VERSION}:{digest}"

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from redis.asyncio import Redis
            except ImportError:
                logger.warning("Redis library is unavailable; artifact cache is disabled")
                return None
            self._client = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
        return self._client

    async def get(self, key: str) -> dict[str, Any] | None:
        if not self.enabled:
            logger.debug("Redis artifact cache is disabled")
            return None
        try:
            client = self._get_client()
            if client is None:
                return None
            raw = await client.get(key)
            if raw is None:
                logger.info("Redis artifact cache miss")
                return None
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("cached artifact is not an object")
            logger.info("Redis artifact cache hit")
            return value
        except Exception:
            logger.exception("Redis artifact cache read failed")
            return None

    async def set(self, key: str, value: dict[str, Any]) -> None:
        if not self.enabled:
            return
        try:
            client = self._get_client()
            if client is None:
                return
            await client.set(
                key,
                json.dumps(value, separators=(",", ":")),
                ex=settings.REDIS_ARTIFACT_TTL_SECONDS,
            )
            logger.info("Redis artifact cache set")
        except Exception:
            logger.exception("Redis artifact cache write failed")

    async def delete(self, key: str) -> None:
        if not self.enabled:
            return
        try:
            client = self._get_client()
            if client is not None:
                await client.delete(key)
        except Exception:
            logger.exception("Redis artifact cache delete failed")


artifact_cache = ArtifactCache()

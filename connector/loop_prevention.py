"""Módulo para evitar bucles infinitos de sincronización."""

from __future__ import annotations

import time

import redis

from connector.config import get_settings
from connector.utils import get_logger

logger = get_logger(__name__)


def _get_redis_client() -> redis.Redis:
    """Crea un cliente Redis a partir de la configuración global."""
    return redis.Redis.from_url(get_settings().celery_broker)


def should_sync(entity_type: str, entity_id: str | int, direction: str, cooldown: int = 30) -> bool:
    """Indica si un evento debe sincronizarse o si parece un eco reciente."""
    key = f"sync:{entity_type}:{entity_id}:{direction}"
    try:
        client = _get_redis_client()
        if client.exists(key):
            logger.info("Evento bloqueado por prevención de loop: %s", key)
            return False
        client.setex(key, cooldown, int(time.time()))
        return True
    except redis.RedisError as exc:
        logger.warning("No se pudo consultar Redis, se permite sincronización por seguridad operativa: %s", exc)
        return True

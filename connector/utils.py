"""Utilidades compartidas del middleware."""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Iterable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def get_logger(name: str) -> logging.Logger:
    """Retorna un logger con configuración estándar."""
    return logging.getLogger(name)


def validate_required_fields(data: dict[str, Any], fields: Iterable[str]) -> None:
    """Valida que un payload tenga los campos obligatorios."""
    missing = [field for field in fields if data.get(field) in (None, "")]
    if missing:
        raise ValueError(f"Faltan campos obligatorios: {', '.join(missing)}")


def retry(retries: int = 3, delay: int = 1) -> Callable[[F], F]:
    """Decorador de reintento genérico para operaciones transitorias."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger(func.__module__)
            last_error: Exception | None = None
            for attempt in range(1, retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # pragma: no cover
                    last_error = exc
                    logger.warning("Intento %s/%s fallido en %s: %s", attempt, retries, func.__name__, exc)
                    if attempt < retries:
                        time.sleep(delay)
            assert last_error is not None
            raise last_error

        return wrapper  # type: ignore[return-value]

    return decorator

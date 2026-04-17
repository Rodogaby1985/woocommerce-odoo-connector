"""Configuración centralizada para el conector."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Representa la configuración del middleware leída desde variables de entorno."""

    wc_url: str
    wc_consumer_key: str
    wc_consumer_secret: str
    odoo_url: str
    odoo_db: str
    odoo_user: str
    odoo_password: str
    webhook_secret: str
    odoo_api_key: str = ""
    odoo_protocol: str = "auto"
    odoo_sale_pricelist_id: int = 0
    price_strategy: str = "custom_fields"
    celery_broker: str = "redis://localhost:6379/0"
    odoo_version: int = 18

    @classmethod
    def from_env(cls) -> "Settings":
        """Construye la configuración usando variables de entorno obligatorias."""
        values = {
            "wc_url": os.getenv("WC_URL", ""),
            "wc_consumer_key": os.getenv("WC_CONSUMER_KEY", ""),
            "wc_consumer_secret": os.getenv("WC_CONSUMER_SECRET", ""),
            "odoo_url": os.getenv("ODOO_URL", ""),
            "odoo_db": os.getenv("ODOO_DB", ""),
            "odoo_user": os.getenv("ODOO_USER", ""),
            "odoo_password": os.getenv("ODOO_PASSWORD", ""),
            "odoo_api_key": os.getenv("ODOO_API_KEY", ""),
            "odoo_protocol": os.getenv("ODOO_PROTOCOL", "auto"),
            "odoo_sale_pricelist_id": int(os.getenv("ODOO_SALE_PRICELIST_ID", "0")),
            "price_strategy": os.getenv("PRICE_STRATEGY", "custom_fields"),
            "webhook_secret": os.getenv("WEBHOOK_SECRET", ""),
            "celery_broker": os.getenv("CELERY_BROKER", "redis://localhost:6379/0"),
            "odoo_version": int(os.getenv("ODOO_VERSION", "18")),
        }
        return cls(**values)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Obtiene la configuración en caché para reutilizarla en toda la app."""
    return Settings.from_env()

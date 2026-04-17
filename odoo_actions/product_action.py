"""Automated Action de Odoo para notificar cambios de productos al middleware."""

from __future__ import annotations

import requests

MIDDLEWARE_URL = "http://middleware:8000/webhook/odoo"


def notify_product_change(record: object) -> None:
    """Envía evento product.write al middleware."""
    payload = {
        "event": "product.write",
        "data": {
            "id": record.id,
            "name": getattr(record, "name", ""),
            "default_code": getattr(record, "default_code", ""),
            "list_price": getattr(record, "list_price", 0),
            "qty_available": getattr(record, "qty_available", 0),
            "x_wc_id": getattr(record, "x_wc_id", None),
        },
    }
    requests.post(MIDDLEWARE_URL, json=payload, timeout=10)

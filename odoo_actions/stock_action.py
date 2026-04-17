"""Automated Action de Odoo para cambios de stock."""

from __future__ import annotations

import requests

MIDDLEWARE_URL = "http://middleware:8000/webhook/odoo"


def notify_stock_change(record: object) -> None:
    """Envía evento stock.change al middleware."""
    payload = {
        "event": "stock.change",
        "data": {
            "product_id": getattr(record, "product_id", None).id if getattr(record, "product_id", None) else None,
            "qty_available": getattr(record, "quantity", 0),
        },
    }
    requests.post(MIDDLEWARE_URL, json=payload, timeout=10)

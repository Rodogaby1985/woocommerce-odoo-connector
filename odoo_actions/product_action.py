"""Automated Action de Odoo para notificar cambios de productos al middleware."""

from __future__ import annotations

import requests

MIDDLEWARE_URL = "http://middleware:8000/webhook/odoo"


def notify_product_change(record: object) -> None:
    """Envía evento product.write al middleware."""
    attribute_lines = []
    for line in getattr(record, "attribute_line_ids", []):
        attribute_lines.append(
            {
                "attribute_name": getattr(getattr(line, "attribute_id", None), "name", ""),
                "values": [getattr(value, "name", "") for value in getattr(line, "value_ids", [])],
            }
        )
    payload = {
        "event": "product.write",
        "data": {
            "id": record.id,
            "name": getattr(record, "name", ""),
            "default_code": getattr(record, "default_code", ""),
            "list_price": getattr(record, "list_price", 0),
            "x_sale_price": getattr(record, "x_sale_price", 0),
            "x_sale_date_from": str(getattr(record, "x_sale_date_from", "")) or "",
            "x_sale_date_to": str(getattr(record, "x_sale_date_to", "")) or "",
            "qty_available": getattr(record, "qty_available", 0),
            "x_wc_id": getattr(record, "x_wc_id", None),
            "product_variant_ids": [variant.id for variant in getattr(record, "product_variant_ids", [])],
            "template_attribute_lines": attribute_lines,
        },
    }
    requests.post(MIDDLEWARE_URL, json=payload, timeout=10)

"""Automated Action de Odoo para notificar cambios de variantes al middleware."""

from __future__ import annotations

import requests

MIDDLEWARE_URL = "http://middleware:8000/webhook/odoo"


def notify_variant_change(record: object) -> None:
    """Envía evento variant.write con precio/stock/atributos de una variante."""
    template = getattr(record, "product_tmpl_id", None)
    attribute_values = []
    for attribute_value in getattr(record, "product_template_attribute_value_ids", []):
        attribute_values.append(
            {
                "name": getattr(getattr(attribute_value, "attribute_id", None), "name", ""),
                "value": getattr(getattr(attribute_value, "product_attribute_value_id", None), "name", ""),
            }
        )

    payload = {
        "event": "variant.write",
        "data": {
            "variant_id": record.id,
            "product_id": getattr(template, "id", None),
            "default_code": getattr(record, "default_code", ""),
            "qty_available": getattr(record, "qty_available", 0),
            "lst_price": getattr(record, "lst_price", 0),
            "x_wc_variation_id": getattr(record, "x_wc_variation_id", None),
            "x_wc_id": getattr(template, "x_wc_id", None),
            "variant_attributes": attribute_values,
        },
    }
    requests.post(MIDDLEWARE_URL, json=payload, timeout=10)

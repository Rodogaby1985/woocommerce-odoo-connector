"""Utilidades de compatibilidad entre versiones de Odoo."""

from __future__ import annotations

FIELD_COMPAT_V19 = {
    "product_uom": "product_uom_id",
}


def normalize_field(field_name: str, odoo_version: int = 18) -> str:
    """Normaliza nombres de campos según versión de Odoo."""
    if odoo_version >= 19:
        return FIELD_COMPAT_V19.get(field_name, field_name)
    return field_name

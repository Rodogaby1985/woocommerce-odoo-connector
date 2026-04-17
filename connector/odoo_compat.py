"""Compatibilidad de nombres de campos entre versiones de Odoo."""

from __future__ import annotations

FIELD_COMPAT = {
    "product_uom": "product_uom_id",
}


def normalize_field(field_name: str, odoo_version: int = 18) -> str:
    """Retorna el nombre correcto del campo según la versión de Odoo."""
    if odoo_version >= 19:
        return FIELD_COMPAT.get(field_name, field_name)
    return field_name


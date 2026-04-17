"""Transformaciones entre estructuras de WooCommerce y Odoo."""

from __future__ import annotations

from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class ProductMapper:
    """Mapea productos entre WooCommerce y Odoo."""

    @staticmethod
    def wc_to_odoo(product: dict[str, Any]) -> dict[str, Any]:
        """Convierte un producto de WooCommerce a formato Odoo."""
        categories = product.get("categories", [])
        category_id = categories[0].get("id") if categories else False
        return {
            "name": product.get("name"),
            "default_code": product.get("sku"),
            "list_price": _to_float(product.get("regular_price") or product.get("price")),
            "description_sale": product.get("description") or product.get("short_description"),
            "qty_available": _to_float(product.get("stock_quantity")),
            "categ_id": category_id,
            "x_wc_id": product.get("id"),
        }

    @staticmethod
    def odoo_to_wc(product: dict[str, Any]) -> dict[str, Any]:
        """Convierte un producto de Odoo a formato WooCommerce."""
        categ_id = product.get("categ_id")
        wc_categories: list[dict[str, Any]] = []
        if isinstance(categ_id, (list, tuple)) and categ_id:
            wc_categories = [{"id": categ_id[0]}]
        elif isinstance(categ_id, int):
            wc_categories = [{"id": categ_id}]

        return {
            "name": product.get("name"),
            "sku": product.get("default_code"),
            "regular_price": str(_to_float(product.get("list_price"))),
            "description": product.get("description_sale") or "",
            "stock_quantity": int(_to_float(product.get("qty_available"))),
            "manage_stock": True,
            "categories": wc_categories,
        }


class OrderMapper:
    """Mapea pedidos de WooCommerce a Odoo."""

    STATUS_MAP = {
        "pending": "draft",
        "processing": "sale",
        "completed": "done",
        "cancelled": "cancel",
    }

    @classmethod
    def wc_to_odoo(
        cls,
        order: dict[str, Any],
        partner_id: int,
        product_id_map: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Convierte un pedido de WooCommerce a estructura de sale.order."""
        product_id_map = product_id_map or {}
        lines = []
        for item in order.get("line_items", []):
            sku = item.get("sku")
            mapped_product_id = product_id_map.get(sku or "", 0)
            lines.append(
                (
                    0,
                    0,
                    {
                        "name": item.get("name"),
                        "product_id": mapped_product_id,
                        "product_uom_qty": _to_float(item.get("quantity"), default=1),
                        "price_unit": _to_float(item.get("price")),
                    },
                )
            )

        return {
            "partner_id": partner_id,
            "origin": f"WC-{order.get('id')}",
            "client_order_ref": str(order.get("id")),
            "order_line": lines,
            "amount_total": _to_float(order.get("total")),
            "state": cls.STATUS_MAP.get(order.get("status"), "draft"),
        }


class CustomerMapper:
    """Mapea clientes entre WooCommerce y Odoo."""

    @staticmethod
    def wc_to_odoo(customer: dict[str, Any]) -> dict[str, Any]:
        """Convierte un cliente WooCommerce a res.partner."""
        billing = customer.get("billing", {})
        first_name = billing.get("first_name") or customer.get("first_name") or ""
        last_name = billing.get("last_name") or customer.get("last_name") or ""
        full_name = (f"{first_name} {last_name}").strip() or customer.get("username") or "Cliente"
        return {
            "name": full_name,
            "email": customer.get("email") or billing.get("email"),
            "phone": billing.get("phone") or customer.get("phone"),
            "street": billing.get("address_1"),
            "street2": billing.get("address_2"),
            "city": billing.get("city"),
            "state_id": billing.get("state"),
            "zip": billing.get("postcode"),
            "country_id": billing.get("country"),
            "x_wc_id": customer.get("id"),
        }

    @staticmethod
    def odoo_to_wc(customer: dict[str, Any]) -> dict[str, Any]:
        """Convierte un partner de Odoo a cliente WooCommerce."""
        full_name = customer.get("name") or ""
        parts = full_name.split(" ", 1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""

        return {
            "email": customer.get("email"),
            "first_name": first_name,
            "last_name": last_name,
            "billing": {
                "first_name": first_name,
                "last_name": last_name,
                "phone": customer.get("phone") or "",
                "address_1": customer.get("street") or "",
                "address_2": customer.get("street2") or "",
                "city": customer.get("city") or "",
                "state": customer.get("state_id") or "",
                "postcode": customer.get("zip") or "",
                "country": customer.get("country_id") or "",
                "email": customer.get("email") or "",
            },
        }

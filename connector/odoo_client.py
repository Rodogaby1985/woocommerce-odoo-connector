"""Cliente para operaciones sobre Odoo con transporte compatible 18/19."""

from __future__ import annotations

from typing import Any

from connector.config import get_settings
from connector.odoo_compat import normalize_field
from connector.odoo_transport import create_transport


class OdooClient:
    """Encapsula operaciones sobre modelos de Odoo."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.transport = create_transport(
            url=self.settings.odoo_url,
            db=self.settings.odoo_db,
            user=self.settings.odoo_user,
            password=self.settings.odoo_password,
            api_key=self.settings.odoo_api_key or None,
            protocol=self.settings.odoo_protocol,
        )
        self.odoo_version = 19 if (self.settings.odoo_protocol or "").lower() == "jsonrpc" else 18

    def _prepare_kwargs(self, kwargs: dict[str, Any] | None = None) -> dict[str, Any]:
        params = dict(kwargs or {})
        fields = params.get("fields")
        if isinstance(fields, list):
            params["fields"] = [normalize_field(str(field), self.odoo_version) for field in fields]
        return params

    def execute(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> Any:
        """Ejecuta un método RPC sobre un modelo."""
        return self.transport.execute_kw(model, method, args, self._prepare_kwargs(kwargs))

    def get_product(self, product_id: int) -> dict[str, Any]:
        """Obtiene un producto por ID."""
        fields = [
            "id",
            "name",
            "default_code",
            "list_price",
            "x_sale_price",
            "x_sale_date_from",
            "x_sale_date_to",
            "description_sale",
            "qty_available",
            "categ_id",
            "x_wc_id",
            "product_variant_ids",
            "attribute_line_ids",
        ]
        result = self.execute("product.template", "read", [[product_id]], {"fields": fields, "limit": 1})
        return result[0] if result else {}

    def create_product(self, payload: dict[str, Any]) -> int:
        """Crea un producto en Odoo."""
        return int(self.execute("product.template", "create", [payload]))

    def update_product(self, product_id: int, payload: dict[str, Any]) -> bool:
        """Actualiza un producto en Odoo."""
        return bool(self.execute("product.template", "write", [[product_id], payload]))

    def find_product_by_sku(self, sku: str) -> dict[str, Any] | None:
        """Busca un producto por SKU (default_code)."""
        result = self.execute("product.template", "search_read", [[("default_code", "=", sku)]], {"limit": 1})
        return result[0] if result else None

    def _get_sale_pricelist_id(self) -> int:
        return int(self.settings.odoo_sale_pricelist_id or 0)

    def get_sale_price(self, product_id: int) -> dict[str, Any] | None:
        """Obtiene el precio oferta activo desde una lista de precios."""
        pricelist_id = self._get_sale_pricelist_id()
        if not pricelist_id:
            return None
        items = self.execute(
            "product.pricelist.item",
            "search_read",
            [[("pricelist_id", "=", pricelist_id), ("product_tmpl_id", "=", product_id)]],
            {"fields": ["id", "fixed_price", "date_start", "date_end"], "limit": 1},
        )
        if not items:
            return None
        item = items[0]
        return {
            "item_id": int(item["id"]),
            "price": float(item.get("fixed_price") or 0.0),
            "date_from": item.get("date_start") or "",
            "date_to": item.get("date_end") or "",
        }

    def set_sale_price(
        self,
        product_id: int,
        price: float,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> bool:
        """Crea o actualiza un item de lista de precios para oferta."""
        pricelist_id = self._get_sale_pricelist_id()
        if not pricelist_id:
            return False
        payload = {
            "pricelist_id": pricelist_id,
            "applied_on": "1_product",
            "product_tmpl_id": product_id,
            "compute_price": "fixed",
            "fixed_price": float(price),
            "date_start": date_from or False,
            "date_end": date_to or False,
        }
        existing = self.get_sale_price(product_id)
        if existing:
            return bool(self.execute("product.pricelist.item", "write", [[existing["item_id"]], payload]))
        self.execute("product.pricelist.item", "create", [payload])
        return True

    def clear_sale_price(self, product_id: int) -> bool:
        """Elimina precio oferta en lista de precios."""
        existing = self.get_sale_price(product_id)
        if not existing:
            return True
        return bool(self.execute("product.pricelist.item", "unlink", [[existing["item_id"]]]))

    def read_stock_quant(self, product_id: int, location_id: int = 1) -> dict[str, Any] | None:
        """Lee el stock en stock.quant para un producto/location."""
        quants = self.execute(
            "stock.quant",
            "search_read",
            [[("product_id", "=", product_id), ("location_id", "=", location_id)]],
            {"limit": 1},
        )
        return quants[0] if quants else None

    def update_inventory_quantity(self, product_id: int, quantity: float, location_id: int = 1) -> bool:
        """Actualiza o crea un registro de inventario en stock.quant."""
        quant = self.read_stock_quant(product_id, location_id)
        if quant:
            return bool(self.execute("stock.quant", "write", [[quant["id"]], {"inventory_quantity": quantity}]))
        self.execute(
            "stock.quant",
            "create",
            [{"product_id": product_id, "location_id": location_id, "inventory_quantity": quantity}],
        )
        return True

    def create_sale_order(self, payload: dict[str, Any]) -> int:
        """Crea un pedido de venta."""
        return int(self.execute("sale.order", "create", [payload]))

    def confirm_sale_order(self, order_id: int) -> bool:
        """Confirma un pedido de venta."""
        self.execute("sale.order", "action_confirm", [[order_id]])
        return True

    def cancel_sale_order(self, order_id: int) -> bool:
        """Cancela un pedido de venta."""
        self.execute("sale.order", "action_cancel", [[order_id]])
        return True

    def get_customer(self, partner_id: int) -> dict[str, Any]:
        """Obtiene un cliente por ID."""
        result = self.execute("res.partner", "read", [[partner_id]], {"limit": 1})
        return result[0] if result else {}

    def create_customer(self, payload: dict[str, Any]) -> int:
        """Crea un cliente en Odoo."""
        return int(self.execute("res.partner", "create", [payload]))

    def update_customer(self, partner_id: int, payload: dict[str, Any]) -> bool:
        """Actualiza un cliente."""
        return bool(self.execute("res.partner", "write", [[partner_id], payload]))

    def find_customer_by_email(self, email: str) -> dict[str, Any] | None:
        """Busca cliente por email."""
        result = self.execute("res.partner", "search_read", [[("email", "=", email)]], {"limit": 1})
        return result[0] if result else None

    def get_categories(self) -> list[dict[str, Any]]:
        """Obtiene categorías de producto."""
        return self.execute("product.category", "search_read", [[]], {})

    def create_category(self, payload: dict[str, Any]) -> int:
        """Crea categoría en Odoo."""
        return int(self.execute("product.category", "create", [payload]))

    def update_category(self, category_id: int, payload: dict[str, Any]) -> bool:
        """Actualiza categoría."""
        return bool(self.execute("product.category", "write", [[category_id], payload]))

    def delete_category(self, category_id: int) -> bool:
        """Elimina categoría."""
        return bool(self.execute("product.category", "unlink", [[category_id]]))

    def get_or_create_attribute(self, name: str) -> int:
        """Busca o crea un atributo de producto por nombre."""
        result = self.execute("product.attribute", "search_read", [[("name", "=", name)]], {"limit": 1})
        if result:
            return int(result[0]["id"])
        return int(self.execute("product.attribute", "create", [{"name": name}]))

    def get_or_create_attribute_value(self, attribute_id: int, name: str) -> int:
        """Busca o crea un valor de atributo."""
        result = self.execute(
            "product.attribute.value",
            "search_read",
            [[("attribute_id", "=", attribute_id), ("name", "=", name)]],
            {"limit": 1},
        )
        if result:
            return int(result[0]["id"])
        return int(self.execute("product.attribute.value", "create", [{"attribute_id": attribute_id, "name": name}]))

    def get_product_variants(self, template_id: int) -> list[dict[str, Any]]:
        """Obtiene variantes de un producto plantilla."""
        variants = self.execute(
            "product.product",
            "search_read",
            [[("product_tmpl_id", "=", template_id)]],
            {
                "fields": [
                    "id",
                    "default_code",
                    "lst_price",
                    "x_sale_price",
                    "x_sale_date_from",
                    "x_sale_date_to",
                    "qty_available",
                    "x_wc_variation_id",
                    "product_template_attribute_value_ids",
                ]
            },
        )
        for variant in variants:
            ptav_ids = variant.get("product_template_attribute_value_ids") or []
            variant["variant_attributes"] = []
            if not ptav_ids:
                continue
            ptav_values = self.execute(
                "product.template.attribute.value",
                "read",
                [ptav_ids],
                {"fields": ["attribute_id", "product_attribute_value_id"]},
            )
            for ptav in ptav_values:
                attribute_id = ptav.get("attribute_id")
                product_attribute_value_id = ptav.get("product_attribute_value_id")
                attribute_name = attribute_id[1] if isinstance(attribute_id, (list, tuple)) and len(attribute_id) > 1 else ""
                value_name = (
                    product_attribute_value_id[1]
                    if isinstance(product_attribute_value_id, (list, tuple)) and len(product_attribute_value_id) > 1
                    else ""
                )
                if attribute_name and value_name:
                    variant["variant_attributes"].append({"name": attribute_name, "value": value_name})
        return variants

    def get_variant_by_wc_id(self, wc_variation_id: int) -> dict[str, Any] | None:
        """Busca una variante por campo técnico x_wc_variation_id."""
        result = self.execute(
            "product.product",
            "search_read",
            [[("x_wc_variation_id", "=", wc_variation_id)]],
            {"limit": 1},
        )
        return result[0] if result else None

    def update_variant(self, variant_id: int, payload: dict[str, Any]) -> bool:
        """Actualiza una variante product.product."""
        return bool(self.execute("product.product", "write", [[variant_id], payload]))

    def get_template_attribute_lines(self, template_id: int) -> list[dict[str, Any]]:
        """Obtiene líneas de atributos de una plantilla."""
        return self.execute(
            "product.template.attribute.line",
            "search_read",
            [[("product_tmpl_id", "=", template_id)]],
            {"fields": ["id", "attribute_id", "value_ids"]},
        )

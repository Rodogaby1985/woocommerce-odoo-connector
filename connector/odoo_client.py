"""Cliente para Odoo con soporte XML-RPC y JSON-RPC."""

from __future__ import annotations

from typing import Any

from connector.config import get_settings
from connector.odoo_compat import normalize_field
from connector.odoo_transport import OdooTransport, create_transport


class OdooClient:
    """Encapsula operaciones sobre modelos de Odoo."""

    def __init__(self) -> None:
        settings = get_settings()
        self.url = settings.odoo_url
        self.db = settings.odoo_db
        self.username = settings.odoo_user
        self.password = settings.odoo_password
        self.api_key = settings.odoo_api_key
        self.protocol = settings.odoo_protocol
        self.odoo_version = settings.odoo_version
        self.sale_pricelist_id = settings.odoo_sale_pricelist_id
        self.price_strategy = settings.price_strategy
        self.transport: OdooTransport = create_transport(
            url=self.url,
            db=self.db,
            user=self.username,
            password=self.password,
            api_key=self.api_key,
            protocol=self.protocol,
        )

    @property
    def uid(self) -> int:
        """Retorna el uid autenticado en el transporte configurado."""
        return self.transport.uid

    def _normalize_fields(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Normaliza nombres de campos para compatibilidad por versión."""
        normalized = dict(kwargs)
        fields = normalized.get("fields")
        if isinstance(fields, list):
            normalized["fields"] = [normalize_field(str(field), self.odoo_version) for field in fields]
        return normalized

    def execute(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> Any:
        """Ejecuta un método sobre un modelo de Odoo."""
        return self.transport.execute_kw(model, method, args, self._normalize_fields(kwargs or {}))

    def get_product(self, product_id: int) -> dict[str, Any]:
        """Obtiene un producto por ID."""
        result = self.execute(
            "product.template",
            "read",
            [[product_id]],
            {
                "fields": [
                    "id",
                    "name",
                    "default_code",
                    "list_price",
                    "description_sale",
                    "qty_available",
                    "categ_id",
                    "x_wc_id",
                    "product_variant_ids",
                    "attribute_line_ids",
                    "x_sale_price",
                    "x_sale_date_from",
                    "x_sale_date_to",
                ],
                "limit": 1,
            },
        )
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
            {"fields": ["id", "default_code", "lst_price", "qty_available", "x_wc_variation_id", "product_template_attribute_value_ids"]},
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

    def get_sale_price(self, product_id: int) -> dict[str, Any] | None:
        """Busca precio de oferta activo en product.pricelist.item."""
        if self.sale_pricelist_id <= 0:
            return None
        items = self.execute(
            "product.pricelist.item",
            "search_read",
            [
                [
                    ("pricelist_id", "=", self.sale_pricelist_id),
                    ("applied_on", "=", "1_product"),
                    ("product_tmpl_id", "=", product_id),
                ]
            ],
            {"fields": ["id", "fixed_price", "date_start", "date_end"], "limit": 1},
        )
        return items[0] if items else None

    def set_sale_price(self, product_id: int, price: float, date_from: str | None = None, date_to: str | None = None) -> None:
        """Crea o actualiza el precio de oferta en pricelist item."""
        if self.sale_pricelist_id <= 0:
            raise ValueError("ODOO_SALE_PRICELIST_ID debe configurarse para estrategia pricelist")
        existing = self.get_sale_price(product_id)
        payload = {
            "pricelist_id": self.sale_pricelist_id,
            "applied_on": "1_product",
            "product_tmpl_id": product_id,
            "compute_price": "fixed",
            "fixed_price": price,
            "date_start": date_from or False,
            "date_end": date_to or False,
        }
        if existing:
            self.execute("product.pricelist.item", "write", [[existing["id"]], payload])
            return
        self.execute("product.pricelist.item", "create", [payload])

    def clear_sale_price(self, product_id: int) -> None:
        """Elimina el precio de oferta de la lista configurada."""
        if self.sale_pricelist_id <= 0:
            return
        existing = self.get_sale_price(product_id)
        if existing:
            self.execute("product.pricelist.item", "unlink", [[existing["id"]]])

"""Cliente XML-RPC para Odoo."""

from __future__ import annotations

import xmlrpc.client
from typing import Any

from connector.config import get_settings


class OdooClient:
    """Encapsula operaciones sobre modelos de Odoo vía XML-RPC."""

    def __init__(self) -> None:
        settings = get_settings()
        self.url = settings.odoo_url
        self.db = settings.odoo_db
        self.username = settings.odoo_user
        self.password = settings.odoo_password
        self._uid: int | None = None
        self.common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    @property
    def uid(self) -> int:
        """Autentica contra Odoo y cachea el uid."""
        if self._uid is None:
            uid = self.common.authenticate(self.db, self.username, self.password, {})
            if not uid:
                raise ConnectionError("No fue posible autenticarse en Odoo")
            self._uid = uid
        return self._uid

    def execute(self, model: str, method: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> Any:
        """Ejecuta un método XML-RPC sobre un modelo."""
        return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs or {})

    def get_product(self, product_id: int) -> dict[str, Any]:
        """Obtiene un producto por ID."""
        result = self.execute("product.template", "read", [[product_id]], {"limit": 1})
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

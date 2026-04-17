"""Cliente para WooCommerce REST API v3."""

from __future__ import annotations

from typing import Any

from woocommerce import API

from connector.config import get_settings


class WooCommerceClient:
    """Encapsula operaciones CRUD contra WooCommerce."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = API(
            url=settings.wc_url,
            consumer_key=settings.wc_consumer_key,
            consumer_secret=settings.wc_consumer_secret,
            version="wc/v3",
            timeout=30,
        )

    @staticmethod
    def _parse_response(response: Any) -> Any:
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        if hasattr(response, "json"):
            return response.json()
        return response

    def get_products(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Obtiene productos de WooCommerce."""
        return self._parse_response(self.client.get("products", params=params or {}))

    def create_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Crea un producto en WooCommerce."""
        return self._parse_response(self.client.post("products", data=payload))

    def update_product(self, product_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Actualiza un producto existente en WooCommerce."""
        return self._parse_response(self.client.put(f"products/{product_id}", data=payload))

    def find_product_by_sku(self, sku: str) -> dict[str, Any] | None:
        """Busca un producto por SKU."""
        products = self.get_products({"sku": sku})
        return products[0] if products else None

    def update_stock(self, product_id: int, quantity: int | float) -> dict[str, Any]:
        """Actualiza el inventario de un producto."""
        return self.update_product(product_id, {"stock_quantity": quantity, "manage_stock": True})

    def get_orders(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Obtiene pedidos."""
        return self._parse_response(self.client.get("orders", params=params or {}))

    def update_order_status(self, order_id: int, status: str) -> dict[str, Any]:
        """Actualiza el estado de un pedido."""
        return self._parse_response(self.client.put(f"orders/{order_id}", data={"status": status}))

    def get_customers(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Obtiene clientes."""
        return self._parse_response(self.client.get("customers", params=params or {}))

    def create_customer(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Crea un cliente."""
        return self._parse_response(self.client.post("customers", data=payload))

    def update_customer(self, customer_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Actualiza un cliente."""
        return self._parse_response(self.client.put(f"customers/{customer_id}", data=payload))

    def get_categories(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Obtiene categorías de productos."""
        return self._parse_response(self.client.get("products/categories", params=params or {}))

    def create_category(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Crea una categoría de producto."""
        return self._parse_response(self.client.post("products/categories", data=payload))

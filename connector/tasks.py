"""Tareas Celery para sincronización bidireccional."""

from __future__ import annotations

from celery import Celery

from connector.config import get_settings
from connector.loop_prevention import should_sync
from connector.mappers import CustomerMapper, OrderMapper, ProductMapper
from connector.odoo_client import OdooClient
from connector.utils import validate_required_fields
from connector.wc_client import WooCommerceClient

settings = get_settings()
celery_app = Celery("connector", broker=settings.celery_broker)


def _wc_client() -> WooCommerceClient:
    return WooCommerceClient()


def _odoo_client() -> OdooClient:
    return OdooClient()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_product_from_wc(self, payload: dict) -> dict:
    """Sincroniza producto de WooCommerce hacia Odoo."""
    try:
        validate_required_fields(payload, ["id", "sku"])
        if not should_sync("product", payload["id"], "wc_to_odoo"):
            return {"status": "skipped", "reason": "loop_prevention"}

        client = _odoo_client()
        mapped = ProductMapper.wc_to_odoo(payload)
        existing = client.find_product_by_sku(payload["sku"])
        if existing:
            client.update_product(existing["id"], mapped)
            return {"status": "updated", "odoo_id": existing["id"]}
        product_id = client.create_product(mapped)
        return {"status": "created", "odoo_id": product_id}
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_customer_from_wc(self, payload: dict) -> dict:
    """Sincroniza cliente de WooCommerce hacia Odoo."""
    try:
        validate_required_fields(payload, ["id", "email"])
        if not should_sync("customer", payload["id"], "wc_to_odoo"):
            return {"status": "skipped", "reason": "loop_prevention"}

        client = _odoo_client()
        mapped = CustomerMapper.wc_to_odoo(payload)
        existing = client.find_customer_by_email(payload["email"])
        if existing:
            client.update_customer(existing["id"], mapped)
            return {"status": "updated", "odoo_id": existing["id"]}
        customer_id = client.create_customer(mapped)
        return {"status": "created", "odoo_id": customer_id}
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_order_from_wc(self, payload: dict) -> dict:
    """Sincroniza pedido de WooCommerce hacia Odoo."""
    try:
        validate_required_fields(payload, ["id", "status"])
        if not should_sync("order", payload["id"], "wc_to_odoo"):
            return {"status": "skipped", "reason": "loop_prevention"}

        odoo = _odoo_client()
        customer_payload = {
            "id": payload.get("customer_id") or payload.get("id"),
            "email": payload.get("billing", {}).get("email"),
            "billing": payload.get("billing", {}),
        }

        if customer_payload["email"]:
            partner = odoo.find_customer_by_email(customer_payload["email"])
            partner_id = partner["id"] if partner else odoo.create_customer(CustomerMapper.wc_to_odoo(customer_payload))
        else:
            partner_id = 1

        mapped_order = OrderMapper.wc_to_odoo(payload, partner_id=partner_id, product_id_map={})
        order_id = odoo.create_sale_order(mapped_order)

        if payload.get("status") in {"processing", "completed"}:
            odoo.confirm_sale_order(order_id)
        elif payload.get("status") == "cancelled":
            odoo.cancel_sale_order(order_id)

        return {"status": "created", "odoo_id": order_id}
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_product_to_wc(self, payload: dict) -> dict:
    """Sincroniza producto de Odoo hacia WooCommerce."""
    try:
        validate_required_fields(payload, ["id"])
        if not should_sync("product", payload["id"], "odoo_to_wc"):
            return {"status": "skipped", "reason": "loop_prevention"}

        odoo = _odoo_client()
        wc = _wc_client()
        product = odoo.get_product(payload["id"])
        mapped = ProductMapper.odoo_to_wc(product)
        wc_id = payload.get("x_wc_id") or product.get("x_wc_id")
        if wc_id:
            wc.update_product(int(wc_id), mapped)
            return {"status": "updated", "wc_id": int(wc_id)}

        created = wc.create_product(mapped)
        created_id = int(created["id"])
        odoo.update_product(payload["id"], {"x_wc_id": created_id})
        return {"status": "created", "wc_id": created_id}
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_stock_to_wc(self, payload: dict) -> dict:
    """Sincroniza stock de Odoo hacia WooCommerce."""
    try:
        validate_required_fields(payload, ["product_id"])
        if not should_sync("stock", payload["product_id"], "odoo_to_wc"):
            return {"status": "skipped", "reason": "loop_prevention"}

        odoo = _odoo_client()
        wc = _wc_client()
        product = odoo.get_product(payload["product_id"])
        wc_id = payload.get("wc_id") or product.get("x_wc_id")
        if not wc_id:
            return {"status": "skipped", "reason": "missing_wc_id"}

        quantity = payload.get("qty_available")
        if quantity is None:
            quantity = product.get("qty_available", 0)
        wc.update_stock(int(wc_id), quantity)
        return {"status": "updated", "wc_id": int(wc_id), "qty": quantity}
    except Exception as exc:
        raise self.retry(exc=exc)

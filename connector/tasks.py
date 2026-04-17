"""Tareas Celery para sincronización bidireccional."""

from __future__ import annotations

from typing import Any

from celery import Celery

from connector.config import get_settings
from connector.loop_prevention import should_sync
from connector.mappers import CustomerMapper, OrderMapper, ProductMapper, VariantMapper
from connector.odoo_client import OdooClient
from connector.utils import validate_required_fields
from connector.wc_client import WooCommerceClient

settings = get_settings()
celery_app = Celery("connector", broker=settings.celery_broker)


def _wc_client() -> WooCommerceClient:
    return WooCommerceClient()


def _odoo_client() -> OdooClient:
    return OdooClient()


def _build_attribute_line_ids(
    odoo: OdooClient,
    attributes: list[dict[str, Any]],
) -> list[tuple[int, int, dict[str, Any]]]:
    """Construye comandos Odoo para attribute_line_ids."""
    lines: list[tuple[int, int, dict[str, Any]]] = []
    for attribute in attributes:
        values = attribute.get("values") or []
        if not attribute.get("attribute_name") or not values:
            continue
        attribute_id = odoo.get_or_create_attribute(attribute["attribute_name"])
        value_ids = [odoo.get_or_create_attribute_value(attribute_id, value) for value in values]
        lines.append((0, 0, {"attribute_id": attribute_id, "value_ids": [(6, 0, value_ids)]}))
    return lines


def _is_variable_product(template: dict[str, Any]) -> bool:
    """Indica si una plantilla Odoo debe sincronizarse como variable."""
    variant_ids = template.get("product_variant_ids") or []
    return len(variant_ids) > 1 or bool(template.get("attribute_line_ids")) or bool(template.get("template_attribute_lines"))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_product_from_wc(self, payload: dict) -> dict:
    """Sincroniza producto de WooCommerce hacia Odoo."""
    try:
        if payload.get("type") == "variable":
            return sync_variable_product_from_wc.run(payload=payload)

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
def sync_variable_product_from_wc(self, payload: dict) -> dict:
    """Sincroniza un producto variable desde WooCommerce hacia Odoo."""
    try:
        validate_required_fields(payload, ["id"])
        if not should_sync("product", payload["id"], "wc_to_odoo"):
            return {"status": "skipped", "reason": "loop_prevention"}

        odoo = _odoo_client()
        wc = _wc_client()

        mapped_template = ProductMapper.wc_to_odoo(payload)
        raw_attributes = mapped_template.pop("attribute_line_ids", [])
        mapped_template["attribute_line_ids"] = _build_attribute_line_ids(odoo, raw_attributes)

        existing_template = odoo.find_product_by_sku(payload.get("sku", "")) if payload.get("sku") else None
        if existing_template:
            template_id = int(existing_template["id"])
            odoo.update_product(template_id, mapped_template)
        else:
            template_id = odoo.create_product(mapped_template)

        variations = wc.get_variations(payload["id"])
        synced_variants = 0
        for variation in variations:
            mapped_variant = VariantMapper.wc_variation_to_odoo(variation)
            mapped_variant.pop("variant_attributes", None)
            mapped_variant["product_tmpl_id"] = template_id
            existing_variant = None
            if variation.get("id"):
                existing_variant = odoo.get_variant_by_wc_id(int(variation["id"]))

            if existing_variant:
                odoo.update_variant(existing_variant["id"], mapped_variant)
            else:
                odoo.execute("product.product", "create", [mapped_variant])
            synced_variants += 1

        return {"status": "updated" if existing_template else "created", "odoo_id": template_id, "variants": synced_variants}
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
        product = odoo.get_product(payload["id"])
        if _is_variable_product(product):
            variable_payload = dict(payload)
            variable_payload["x_wc_id"] = payload.get("x_wc_id") or product.get("x_wc_id")
            return sync_variable_product_to_wc.run(payload=variable_payload)

        wc = _wc_client()
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
def sync_variable_product_to_wc(self, payload: dict) -> dict:
    """Sincroniza producto variable desde Odoo hacia WooCommerce."""
    try:
        validate_required_fields(payload, ["id"])
        if not should_sync("product", payload["id"], "odoo_to_wc"):
            return {"status": "skipped", "reason": "loop_prevention"}

        odoo = _odoo_client()
        wc = _wc_client()
        template = odoo.get_product(payload["id"])
        template["template_attribute_lines"] = odoo.get_template_attribute_lines(payload["id"])

        mapped_template = ProductMapper.odoo_to_wc(template)
        mapped_template["type"] = "variable"
        wc_id = payload.get("x_wc_id") or template.get("x_wc_id")
        if wc_id:
            wc_template = wc.update_product(int(wc_id), mapped_template)
            template_wc_id = int(wc_template["id"])
        else:
            wc_template = wc.create_product(mapped_template)
            template_wc_id = int(wc_template["id"])
            odoo.update_product(payload["id"], {"x_wc_id": template_wc_id})

        variants = odoo.get_product_variants(payload["id"])
        synced_variants = 0
        for variant in variants:
            mapped_variation = VariantMapper.odoo_variant_to_wc_variation(variant)
            wc_variation_id = variant.get("x_wc_variation_id")
            if wc_variation_id:
                wc.update_variation(template_wc_id, int(wc_variation_id), mapped_variation)
            else:
                created = wc.create_variation(template_wc_id, mapped_variation)
                if created.get("id"):
                    odoo.update_variant(variant["id"], {"x_wc_variation_id": created["id"]})
            synced_variants += 1

        return {"status": "updated" if wc_id else "created", "wc_id": template_wc_id, "variants": synced_variants}
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


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_variant_stock_to_wc(self, payload: dict) -> dict:
    """Sincroniza stock de una variante individual de Odoo hacia WooCommerce."""
    try:
        validate_required_fields(payload, ["variant_id"])
        if not should_sync("variant_stock", payload["variant_id"], "odoo_to_wc"):
            return {"status": "skipped", "reason": "loop_prevention"}

        odoo = _odoo_client()
        wc = _wc_client()
        variants = odoo.execute(
            "product.product",
            "read",
            [[payload["variant_id"]]],
            {"fields": ["id", "qty_available", "x_wc_variation_id", "product_tmpl_id"]},
        )
        if not variants:
            return {"status": "skipped", "reason": "missing_variant"}

        variant = variants[0]
        wc_variation_id = payload.get("wc_variation_id") or variant.get("x_wc_variation_id")
        if not wc_variation_id:
            return {"status": "skipped", "reason": "missing_wc_variation_id"}

        product_tmpl_id = variant.get("product_tmpl_id")
        if isinstance(product_tmpl_id, (list, tuple)):
            product_tmpl_id = product_tmpl_id[0] if product_tmpl_id else None
        template = odoo.get_product(product_tmpl_id) if product_tmpl_id else {}
        wc_product_id = payload.get("wc_product_id") or template.get("x_wc_id")
        if not wc_product_id:
            return {"status": "skipped", "reason": "missing_wc_product_id"}

        qty = payload.get("qty_available")
        if qty is None:
            qty = variant.get("qty_available", 0)
        wc.update_variation(int(wc_product_id), int(wc_variation_id), {"manage_stock": True, "stock_quantity": qty})
        return {
            "status": "updated",
            "wc_id": int(wc_product_id),
            "wc_variation_id": int(wc_variation_id),
            "qty": qty,
        }
    except Exception as exc:
        raise self.retry(exc=exc)

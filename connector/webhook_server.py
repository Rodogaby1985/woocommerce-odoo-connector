"""Servidor Flask que recibe webhooks de WooCommerce y eventos de Odoo."""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any

from flask import Flask, jsonify, request

from connector.config import get_settings
from connector.tasks import celery_app

WC_TOPIC_TASK_MAP = {
    "product.created": "connector.tasks.sync_product_from_wc",
    "product.updated": "connector.tasks.sync_product_from_wc",
    "product.restored": "connector.tasks.sync_product_from_wc",
    "order.created": "connector.tasks.sync_order_from_wc",
    "order.updated": "connector.tasks.sync_order_from_wc",
    "customer.created": "connector.tasks.sync_customer_from_wc",
    "customer.updated": "connector.tasks.sync_customer_from_wc",
}

ODOO_EVENT_TASK_MAP = {
    "product.write": "connector.tasks.sync_product_to_wc",
    "product.create": "connector.tasks.sync_product_to_wc",
    "variant.write": "connector.tasks.sync_variant_stock_to_wc",
    "stock.change": "connector.tasks.sync_stock_to_wc",
}


def verify_wc_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Verifica la firma HMAC-SHA256 enviada por WooCommerce."""
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature or "")


def create_flask_app(celery_instance: Any = None) -> Flask:
    """Crea y configura la aplicación Flask de webhooks."""
    app = Flask(__name__)
    celery_ref = celery_instance or celery_app

    @app.post("/webhook/woocommerce")
    def woocommerce_webhook() -> tuple[Any, int]:
        settings = get_settings()
        signature = request.headers.get("X-WC-Webhook-Signature", "")
        if not verify_wc_signature(request.get_data(), signature, settings.webhook_secret):
            return jsonify({"status": "error", "message": "firma inválida"}), 401

        topic = request.headers.get("X-WC-Webhook-Topic", "")
        payload = request.get_json(silent=True) or {}
        task_name = WC_TOPIC_TASK_MAP.get(topic)

        if not task_name:
            return jsonify({"status": "ignored", "topic": topic}), 202

        celery_ref.send_task(task_name, kwargs={"payload": payload})
        return jsonify({"status": "accepted", "topic": topic}), 202

    @app.post("/webhook/odoo")
    def odoo_webhook() -> tuple[Any, int]:
        payload = request.get_json(silent=True) or {}
        event = payload.get("event")
        data = payload.get("data", {})
        task_name = ODOO_EVENT_TASK_MAP.get(event)

        if not task_name:
            return jsonify({"status": "ignored", "event": event}), 202

        celery_ref.send_task(task_name, kwargs={"payload": data})
        return jsonify({"status": "accepted", "event": event}), 202

    @app.get("/health")
    def health() -> tuple[Any, int]:
        return jsonify({"status": "ok"}), 200

    return app


app = create_flask_app()

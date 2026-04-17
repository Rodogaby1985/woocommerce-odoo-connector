"""Pruebas para endpoints de webhook."""

from __future__ import annotations

import base64
import hashlib
import hmac
from unittest.mock import MagicMock, patch

from connector.webhook_server import create_flask_app


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


@patch("connector.webhook_server.get_settings")
def test_woocommerce_webhook_valid_signature(get_settings: MagicMock) -> None:
    get_settings.return_value = MagicMock(webhook_secret="secret")
    fake_celery = MagicMock()
    app = create_flask_app(fake_celery)
    client = app.test_client()

    body = b'{"id": 1, "sku": "A"}'
    response = client.post(
        "/webhook/woocommerce",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-WC-Webhook-Signature": _sign(body, "secret"),
            "X-WC-Webhook-Topic": "product.created",
        },
    )

    assert response.status_code == 202
    fake_celery.send_task.assert_called_once()


@patch("connector.webhook_server.get_settings")
def test_woocommerce_webhook_invalid_signature(get_settings: MagicMock) -> None:
    get_settings.return_value = MagicMock(webhook_secret="secret")
    app = create_flask_app(MagicMock())
    client = app.test_client()

    response = client.post(
        "/webhook/woocommerce",
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "X-WC-Webhook-Signature": "bad",
            "X-WC-Webhook-Topic": "product.created",
        },
    )

    assert response.status_code == 401


def test_health_endpoint() -> None:
    app = create_flask_app(MagicMock())
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_odoo_webhook_variant_event() -> None:
    fake_celery = MagicMock()
    app = create_flask_app(fake_celery)
    client = app.test_client()

    response = client.post(
        "/webhook/odoo",
        json={"event": "variant.write", "data": {"variant_id": 20}},
    )

    assert response.status_code == 202
    fake_celery.send_task.assert_called_once_with(
        "connector.tasks.sync_variant_stock_to_wc",
        kwargs={"payload": {"variant_id": 20}},
    )

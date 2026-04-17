"""Paquete principal del conector WooCommerce ↔ Odoo."""

from connector.webhook_server import create_flask_app

__all__ = ["create_flask_app"]

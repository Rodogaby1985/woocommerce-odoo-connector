"""Pruebas para el cliente de Odoo."""

from unittest.mock import MagicMock, patch

from connector.odoo_client import OdooClient


@patch("connector.odoo_client.create_transport")
@patch("connector.odoo_client.get_settings")
def test_find_customer_by_email_with_transport(get_settings: MagicMock, create_transport: MagicMock) -> None:
    get_settings.return_value = MagicMock(
        odoo_url="https://odoo.test",
        odoo_db="db",
        odoo_user="user",
        odoo_password="pass",
        odoo_api_key="",
        odoo_protocol="xmlrpc",
        odoo_sale_pricelist_id=0,
    )
    transport = MagicMock()
    transport.execute_kw.return_value = [{"id": 5, "email": "foo@bar.com"}]
    create_transport.return_value = transport

    client = OdooClient()
    customer = client.find_customer_by_email("foo@bar.com")

    assert customer == {"id": 5, "email": "foo@bar.com"}
    transport.execute_kw.assert_called_once_with(
        "res.partner",
        "search_read",
        [[("email", "=", "foo@bar.com")]],
        {"limit": 1},
    )


@patch("connector.odoo_client.create_transport")
@patch("connector.odoo_client.get_settings")
def test_get_or_create_attribute_creates_when_missing(get_settings: MagicMock, create_transport: MagicMock) -> None:
    get_settings.return_value = MagicMock(
        odoo_url="https://odoo.test",
        odoo_db="db",
        odoo_user="user",
        odoo_password="pass",
        odoo_api_key="",
        odoo_protocol="xmlrpc",
        odoo_sale_pricelist_id=0,
    )
    transport = MagicMock()
    transport.execute_kw.side_effect = [[], 9]
    create_transport.return_value = transport

    client = OdooClient()
    attribute_id = client.get_or_create_attribute("Color")

    assert attribute_id == 9


@patch("connector.odoo_client.create_transport")
@patch("connector.odoo_client.get_settings")
def test_sale_price_pricelist_methods(get_settings: MagicMock, create_transport: MagicMock) -> None:
    get_settings.return_value = MagicMock(
        odoo_url="https://odoo.test",
        odoo_db="db",
        odoo_user="user",
        odoo_password="pass",
        odoo_api_key="",
        odoo_protocol="xmlrpc",
        odoo_sale_pricelist_id=5,
    )
    transport = MagicMock()
    transport.execute_kw.side_effect = [
        [{"id": 11, "fixed_price": 49.9, "date_start": "2026-04-01", "date_end": "2026-04-30"}],
        [{"id": 11, "fixed_price": 49.9, "date_start": "2026-04-01", "date_end": "2026-04-30"}],
        True,
        [{"id": 11, "fixed_price": 49.9, "date_start": "2026-04-01", "date_end": "2026-04-30"}],
        True,
    ]
    create_transport.return_value = transport
    client = OdooClient()

    sale = client.get_sale_price(20)
    assert sale == {"item_id": 11, "price": 49.9, "date_from": "2026-04-01", "date_to": "2026-04-30"}
    assert client.set_sale_price(20, 45.0, "2026-04-01", "2026-04-30") is True
    assert client.clear_sale_price(20) is True

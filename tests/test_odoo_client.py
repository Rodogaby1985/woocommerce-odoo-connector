"""Pruebas para el cliente de Odoo."""

from unittest.mock import MagicMock, patch

from connector.odoo_client import OdooClient


def _settings_mock() -> MagicMock:
    return MagicMock(
        odoo_url="https://odoo.test",
        odoo_db="db",
        odoo_user="user",
        odoo_password="pass",
        odoo_api_key="",
        odoo_protocol="auto",
        odoo_version=18,
        odoo_sale_pricelist_id=7,
        price_strategy="custom_fields",
    )


@patch("connector.odoo_client.create_transport")
@patch("connector.odoo_client.get_settings")
def test_find_customer_by_email(get_settings_mock: MagicMock, create_transport_mock: MagicMock) -> None:
    get_settings_mock.return_value = _settings_mock()
    transport = MagicMock()
    transport.execute_kw.return_value = [{"id": 5, "email": "foo@bar.com"}]
    create_transport_mock.return_value = transport

    client = OdooClient()
    customer = client.find_customer_by_email("foo@bar.com")

    assert customer == {"id": 5, "email": "foo@bar.com"}
    transport.execute_kw.assert_called_once()


@patch("connector.odoo_client.create_transport")
@patch("connector.odoo_client.get_settings")
def test_get_or_create_attribute_creates_when_missing(get_settings_mock: MagicMock, create_transport_mock: MagicMock) -> None:
    get_settings_mock.return_value = _settings_mock()
    transport = MagicMock()
    transport.execute_kw.side_effect = [[], 9]
    create_transport_mock.return_value = transport

    client = OdooClient()
    attribute_id = client.get_or_create_attribute("Color")

    assert attribute_id == 9


@patch("connector.odoo_client.create_transport")
@patch("connector.odoo_client.get_settings")
def test_set_sale_price_updates_existing_item(get_settings_mock: MagicMock, create_transport_mock: MagicMock) -> None:
    get_settings_mock.return_value = _settings_mock()
    transport = MagicMock()
    transport.execute_kw.side_effect = [[{"id": 99, "fixed_price": 10.0}], True]
    create_transport_mock.return_value = transport

    client = OdooClient()
    client.set_sale_price(product_id=10, price=9.9, date_from="2026-01-01", date_to="2026-01-10")

    write_call = transport.execute_kw.call_args_list[1]
    assert write_call.args[0] == "product.pricelist.item"
    assert write_call.args[1] == "write"


@patch("connector.odoo_client.create_transport")
@patch("connector.odoo_client.get_settings")
def test_clear_sale_price_unlinks_item(get_settings_mock: MagicMock, create_transport_mock: MagicMock) -> None:
    get_settings_mock.return_value = _settings_mock()
    transport = MagicMock()
    transport.execute_kw.side_effect = [[{"id": 22}], True]
    create_transport_mock.return_value = transport

    client = OdooClient()
    client.clear_sale_price(product_id=11)

    unlink_call = transport.execute_kw.call_args_list[1]
    assert unlink_call.args[0] == "product.pricelist.item"
    assert unlink_call.args[1] == "unlink"

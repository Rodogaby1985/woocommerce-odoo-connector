"""Pruebas para el cliente de Odoo."""

from unittest.mock import MagicMock, patch

from connector.odoo_client import OdooClient


@patch("connector.odoo_client.get_settings")
@patch("connector.odoo_client.xmlrpc.client.ServerProxy")
def test_find_customer_by_email(proxy_cls: MagicMock, get_settings: MagicMock) -> None:
    get_settings.return_value = MagicMock(
        odoo_url="https://odoo.test",
        odoo_db="db",
        odoo_user="user",
        odoo_password="pass",
    )

    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 7
    model_proxy = MagicMock()
    model_proxy.execute_kw.return_value = [{"id": 5, "email": "foo@bar.com"}]
    proxy_cls.side_effect = [common_proxy, model_proxy]

    client = OdooClient()
    customer = client.find_customer_by_email("foo@bar.com")

    assert customer == {"id": 5, "email": "foo@bar.com"}
    model_proxy.execute_kw.assert_called_once()


@patch("connector.odoo_client.get_settings")
@patch("connector.odoo_client.xmlrpc.client.ServerProxy")
def test_get_or_create_attribute_creates_when_missing(proxy_cls: MagicMock, get_settings: MagicMock) -> None:
    get_settings.return_value = MagicMock(
        odoo_url="https://odoo.test",
        odoo_db="db",
        odoo_user="user",
        odoo_password="pass",
    )

    common_proxy = MagicMock()
    common_proxy.authenticate.return_value = 7
    model_proxy = MagicMock()
    model_proxy.execute_kw.side_effect = [[], 9]
    proxy_cls.side_effect = [common_proxy, model_proxy]

    client = OdooClient()
    attribute_id = client.get_or_create_attribute("Color")

    assert attribute_id == 9

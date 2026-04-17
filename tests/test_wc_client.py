"""Pruebas para el cliente de WooCommerce."""

from unittest.mock import MagicMock, patch

from connector.wc_client import WooCommerceClient


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


@patch("connector.wc_client.get_settings")
@patch("connector.wc_client.API")
def test_find_product_by_sku(api_cls: MagicMock, get_settings: MagicMock) -> None:
    get_settings.return_value = MagicMock(
        wc_url="https://shop.test",
        wc_consumer_key="ck",
        wc_consumer_secret="cs",
    )
    api = MagicMock()
    api.get.return_value = _Resp([{"id": 1, "sku": "ABC"}])
    api_cls.return_value = api

    client = WooCommerceClient()
    product = client.find_product_by_sku("ABC")

    assert product == {"id": 1, "sku": "ABC"}
    api.get.assert_called_once()

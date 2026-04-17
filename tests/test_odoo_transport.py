"""Pruebas para transportes de Odoo."""

from unittest.mock import MagicMock, patch

from connector.odoo_transport import JsonRpcTransport, XmlRpcTransport, create_transport


@patch("connector.odoo_transport.xmlrpc.client.ServerProxy")
def test_xmlrpc_transport_auth_and_execute(proxy_mock: MagicMock) -> None:
    common = MagicMock()
    common.authenticate.return_value = 7
    models = MagicMock()
    models.execute_kw.return_value = [{"id": 10}]
    proxy_mock.side_effect = [common, models]

    transport = XmlRpcTransport(url="https://odoo.test", db="db", user="user", password="pass")
    result = transport.execute_kw("res.partner", "search_read", [[]], {"limit": 1})

    assert result == [{"id": 10}]
    models.execute_kw.assert_called_once()


@patch("connector.odoo_transport.requests.post")
def test_jsonrpc_transport_with_api_key(post_mock: MagicMock) -> None:
    auth_response = MagicMock()
    auth_response.raise_for_status.return_value = None
    auth_response.json.return_value = {"jsonrpc": "2.0", "id": 1, "result": 8}
    execute_response = MagicMock()
    execute_response.raise_for_status.return_value = None
    execute_response.json.return_value = {"jsonrpc": "2.0", "id": 2, "result": [{"id": 1}]}
    post_mock.side_effect = [auth_response, execute_response]

    transport = JsonRpcTransport(url="https://odoo.test", db="db", user="user", api_key="api-key")
    result = transport.execute_kw("res.partner", "search_read", [[]], {"limit": 1})

    assert result == [{"id": 1}]
    assert post_mock.call_args_list[0].kwargs["headers"]["Authorization"] == "Bearer api-key"


def test_create_transport_auto_with_api_key_uses_jsonrpc() -> None:
    transport = create_transport(
        url="https://odoo.test",
        db="db",
        user="user",
        password="",
        api_key="api-key",
        protocol="auto",
    )
    assert isinstance(transport, JsonRpcTransport)


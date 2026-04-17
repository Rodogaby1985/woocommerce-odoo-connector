"""Pruebas para la capa de transporte de Odoo."""

from unittest.mock import MagicMock, patch

from connector.odoo_transport import JsonRpcTransport, XmlRpcTransport, create_transport


@patch("connector.odoo_transport.xmlrpc.client.ServerProxy")
def test_xmlrpc_transport_execute_kw(proxy_cls: MagicMock) -> None:
    common = MagicMock()
    common.authenticate.return_value = 9
    models = MagicMock()
    models.execute_kw.return_value = [{"id": 1}]
    proxy_cls.side_effect = [common, models]

    transport = XmlRpcTransport("https://odoo.test", "db", "user", "pass")
    result = transport.execute_kw("res.partner", "search_read", [[("email", "=", "a@b.com")]], {"limit": 1})

    assert result == [{"id": 1}]
    common.authenticate.assert_called_once()
    models.execute_kw.assert_called_once_with(
        "db",
        9,
        "pass",
        "res.partner",
        "search_read",
        [[("email", "=", "a@b.com")]],
        {"limit": 1},
    )


@patch("connector.odoo_transport.requests.post")
def test_jsonrpc_transport_execute_kw_with_api_key(post_mock: MagicMock) -> None:
    post_mock.side_effect = [
        MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": 7}),
        ),
        MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"result": [{"id": 1}]}),
        ),
    ]
    transport = JsonRpcTransport("https://odoo.test", "db", "user", password="", api_key="api-key")
    result = transport.execute_kw("res.partner", "search_read", [[("email", "=", "a@b.com")]], {"limit": 1})

    assert result == [{"id": 1}]
    assert post_mock.call_count == 2
    headers = post_mock.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer api-key"


def test_create_transport_auto_jsonrpc_with_api_key() -> None:
    transport = create_transport(
        url="https://odoo.test",
        db="db",
        user="user",
        password="pass",
        api_key="api-key",
        protocol="auto",
    )
    assert isinstance(transport, JsonRpcTransport)


def test_create_transport_defaults_to_xmlrpc() -> None:
    transport = create_transport(
        url="https://odoo.test",
        db="db",
        user="user",
        password="pass",
        api_key="",
        protocol="auto",
    )
    assert isinstance(transport, XmlRpcTransport)

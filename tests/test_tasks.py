"""Pruebas para tareas de sincronización."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from connector import tasks


@patch("connector.tasks.should_sync", return_value=True)
def test_sync_product_from_wc_delegates_variable(should_sync_mock: MagicMock) -> None:
    assert should_sync_mock is not None
    with patch.object(tasks.sync_variable_product_from_wc, "run", return_value={"status": "created"}) as run_mock:
        result = tasks.sync_product_from_wc.run(payload={"id": 100, "type": "variable"})

    assert result["status"] == "created"
    run_mock.assert_called_once()


@patch("connector.tasks.should_sync", return_value=True)
@patch("connector.tasks._wc_client")
@patch("connector.tasks._odoo_client")
def test_sync_product_to_wc_delegates_variable(
    odoo_client_factory: MagicMock,
    wc_client_factory_mock: MagicMock,
    should_sync_mock: MagicMock,
) -> None:
    assert wc_client_factory_mock is not None
    assert should_sync_mock is not None
    odoo = MagicMock()
    odoo.get_product.return_value = {"id": 10, "product_variant_ids": [1, 2], "x_wc_id": 77}
    odoo_client_factory.return_value = odoo

    with patch.object(tasks.sync_variable_product_to_wc, "run", return_value={"status": "updated"}) as run_mock:
        result = tasks.sync_product_to_wc.run(payload={"id": 10})

    assert result["status"] == "updated"
    run_mock.assert_called_once()


@patch("connector.tasks.should_sync", return_value=True)
@patch("connector.tasks._wc_client")
@patch("connector.tasks._odoo_client")
def test_sync_variant_stock_to_wc_updates_variation(
    odoo_client_factory: MagicMock,
    wc_client_factory: MagicMock,
    should_sync_mock: MagicMock,
) -> None:
    assert should_sync_mock is not None
    odoo = MagicMock()
    odoo.execute.return_value = [{"id": 20, "qty_available": 8, "x_wc_variation_id": 501, "product_tmpl_id": [10, "Remera"]}]
    odoo.get_product.return_value = {"id": 10, "x_wc_id": 100}
    odoo_client_factory.return_value = odoo

    wc = MagicMock()
    wc_client_factory.return_value = wc

    result = tasks.sync_variant_stock_to_wc.run(payload={"variant_id": 20})

    assert result["status"] == "updated"
    wc.update_variation.assert_called_once_with(100, 501, {"manage_stock": True, "stock_quantity": 8})


@patch("connector.tasks.should_sync", return_value=True)
@patch("connector.tasks._wc_client")
@patch("connector.tasks._odoo_client")
def test_sync_variant_stock_to_wc_handles_integer_template_id(
    odoo_client_factory: MagicMock,
    wc_client_factory: MagicMock,
    should_sync_mock: MagicMock,
) -> None:
    assert should_sync_mock is not None
    odoo = MagicMock()
    odoo.execute.return_value = [{"id": 21, "qty_available": 3, "x_wc_variation_id": 502, "product_tmpl_id": 11}]
    odoo.get_product.return_value = {"id": 11, "x_wc_id": 101}
    odoo_client_factory.return_value = odoo

    wc = MagicMock()
    wc_client_factory.return_value = wc

    result = tasks.sync_variant_stock_to_wc.run(payload={"variant_id": 21})

    assert result["wc_id"] == 101
    wc.update_variation.assert_called_once_with(101, 502, {"manage_stock": True, "stock_quantity": 3})


@patch("connector.tasks.should_sync", return_value=True)
@patch("connector.tasks._odoo_client")
def test_sync_product_from_wc_pricelist_sets_sale_price(
    odoo_client_factory: MagicMock,
    should_sync_mock: MagicMock,
) -> None:
    assert should_sync_mock is not None
    odoo = MagicMock()
    odoo.price_strategy = "pricelist"
    odoo.find_product_by_sku.return_value = {"id": 99}
    odoo_client_factory.return_value = odoo

    result = tasks.sync_product_from_wc.run(
        payload={"id": 1, "sku": "SKU-1", "regular_price": "20", "sale_price": "15", "date_on_sale_from": "2026-01-01"}
    )

    assert result["status"] == "updated"
    odoo.set_sale_price.assert_called_once_with(product_id=99, price=15.0, date_from="2026-01-01", date_to=None)


@patch("connector.tasks.should_sync", return_value=True)
@patch("connector.tasks._wc_client")
@patch("connector.tasks._odoo_client")
def test_sync_product_to_wc_pricelist_uses_pricelist_sale(
    odoo_client_factory: MagicMock,
    wc_client_factory: MagicMock,
    should_sync_mock: MagicMock,
) -> None:
    assert should_sync_mock is not None
    odoo = MagicMock()
    odoo.price_strategy = "pricelist"
    odoo.get_product.return_value = {"id": 10, "name": "Producto", "default_code": "SKU", "list_price": 20, "qty_available": 1}
    odoo.get_sale_price.return_value = {"fixed_price": 10, "date_start": "2026-01-01", "date_end": "2026-01-10"}
    odoo_client_factory.return_value = odoo
    wc = MagicMock()
    wc.create_product.return_value = {"id": 111}
    wc_client_factory.return_value = wc

    result = tasks.sync_product_to_wc.run(payload={"id": 10})

    assert result["status"] == "created"
    sent_payload = wc.create_product.call_args.args[0]
    assert sent_payload["sale_price"] == "10.0"
    assert sent_payload["date_on_sale_from"] == "2026-01-01"

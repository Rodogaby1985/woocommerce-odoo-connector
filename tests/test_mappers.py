"""Pruebas unitarias para mappers."""

from connector.mappers import CustomerMapper, OrderMapper, ProductMapper, VariantMapper


def test_product_mapper_wc_to_odoo() -> None:
    wc_product = {
        "id": 10,
        "name": "Producto A",
        "sku": "SKU-A",
        "regular_price": "19.99",
        "description": "Descripción",
        "stock_quantity": 5,
        "categories": [{"id": 3}],
    }

    mapped = ProductMapper.wc_to_odoo(wc_product)

    assert mapped["name"] == "Producto A"
    assert mapped["default_code"] == "SKU-A"
    assert mapped["list_price"] == 19.99
    assert mapped["qty_available"] == 5.0
    assert mapped["categ_id"] == 3


def test_order_mapper_status_map() -> None:
    order = {"id": 99, "status": "processing", "total": "15.0", "line_items": []}

    mapped = OrderMapper.wc_to_odoo(order, partner_id=1)

    assert mapped["state"] == "sale"
    assert mapped["origin"] == "WC-99"


def test_customer_mapper_odoo_to_wc() -> None:
    customer = {
        "name": "Ana Pérez",
        "email": "ana@example.com",
        "phone": "1234",
        "street": "Calle 1",
        "city": "Madrid",
        "zip": "28001",
        "country_id": "ES",
    }

    mapped = CustomerMapper.odoo_to_wc(customer)

    assert mapped["email"] == "ana@example.com"
    assert mapped["first_name"] == "Ana"
    assert mapped["billing"]["city"] == "Madrid"


def test_variant_mapper_wc_variation_to_odoo() -> None:
    wc_variation = {
        "id": 101,
        "sku": "REM-BAS-S-ROJO",
        "regular_price": "2500",
        "stock_quantity": 15,
        "attributes": [{"name": "Talle", "option": "S"}, {"name": "Color", "option": "Rojo"}],
    }

    mapped = VariantMapper.wc_variation_to_odoo(wc_variation)

    assert mapped["x_wc_variation_id"] == 101
    assert mapped["lst_price"] == 2500.0
    assert mapped["qty_available"] == 15.0
    assert mapped["variant_attributes"][0]["name"] == "Talle"


def test_product_mapper_odoo_to_wc_variable() -> None:
    odoo_template = {
        "name": "Remera Básica",
        "default_code": "REM-BAS",
        "list_price": 2500,
        "description_sale": "Remera de prueba",
        "qty_available": 0,
        "product_variant_ids": [11, 12],
        "template_attribute_lines": [
            {"attribute_name": "Talle", "values": ["S", "M"]},
            {"attribute_name": "Color", "values": ["Rojo", "Azul"]},
        ],
    }

    mapped = ProductMapper.odoo_to_wc(odoo_template)

    assert mapped["type"] == "variable"
    assert mapped["attributes"][0]["name"] == "Talle"

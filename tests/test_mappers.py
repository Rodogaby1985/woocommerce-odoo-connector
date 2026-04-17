"""Pruebas unitarias para mappers."""

from connector.mappers import CustomerMapper, OrderMapper, ProductMapper


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

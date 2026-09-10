import pytest
from pydantic import ValidationError

from common.models import Basket, Merchant, OrderRequest, calculate


def test_server_totals_and_delivery_boundary():
    assert calculate([{"price": 5000, "quantity": 3}])["delivery"] == 0
    assert calculate([{"price": 4999, "quantity": 3}])["total"] == 15347


@pytest.mark.parametrize("quantity", [0, -1, 1.2, "2", True, 10001])
def test_reject_invalid_quantities(quantity):
    with pytest.raises(ValidationError):
        Basket(items=[{"id": "rice", "quantity": quantity}])


def test_reject_duplicate_products_and_client_prices():
    with pytest.raises(ValidationError):
        Basket(items=[{"id": "rice", "quantity": 1}, {"id": "rice", "quantity": 2}])
    with pytest.raises(ValidationError):
        OrderRequest(
            items=[{"id": "rice", "quantity": 1, "price": 1}], expected_total=1, method="card"
        )


def test_invalid_delivery_pin():
    with pytest.raises(ValidationError):
        Merchant(
            businessName="Test",
            owner="Test",
            phone="0712345678",
            type="Retail",
            city="Nairobi",
            address="Street",
            point={"lat": 91, "lng": 36},
        )

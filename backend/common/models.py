from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Point(Input):
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)


class Merchant(Input):
    businessName: str = Field(min_length=1, max_length=100)
    owner: str = Field(min_length=1, max_length=100)
    phone: str = Field(pattern=r"^\+?[0-9 ()-]{7,20}$")
    type: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=500)
    point: Point


class Item(Input):
    id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(strict=True, ge=1, le=10000)


class Basket(Input):
    items: Annotated[list[Item], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def unique_items(self):
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("Each product must appear only once")
        return self


class Allocation(Basket):
    expected_total: int = Field(strict=True, ge=0)


class OrderRequest(Allocation):
    method: Literal["mobile", "card"]
    outcome: Literal["success", "declined"] = "success"


def calculate(items):
    subtotal = sum(p["price"] * p["quantity"] for p in items)
    delivery = 0 if subtotal == 0 or subtotal >= 15000 else 350
    return dict(
        items=items,
        subtotal=subtotal,
        delivery=delivery,
        total=subtotal + delivery,
        count=sum(p["quantity"] for p in items),
        currency="KES",
    )

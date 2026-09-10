"""Run against a disposable seeded stack: TEST_BASE_URL=http://localhost:18080 pytest.
These tests place orders and consume sample stock. They never reset existing data.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest

BASE = os.environ.get("TEST_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE, reason="Set TEST_BASE_URL to a disposable running stack")


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE or "http://unused", timeout=30, trust_env=False) as c:
        yield c


def merchant(client):
    profile = {
        "businessName": "Integration Shop",
        "owner": "Test Merchant",
        "phone": "0712345678",
        "type": "Retail shop",
        "city": "Nairobi",
        "address": "Test Street",
        "point": {"lat": -1.28, "lng": 36.82},
    }
    response = client.post("/api/merchants", json=profile)
    assert response.status_code == 201, response.text
    data = response.json()
    return data["merchant"], {"Authorization": "Bearer " + data["token"]}


def stock(client, product):
    response = client.get("/api/catalog/products")
    assert response.status_code == 200, response.text
    return next(p["stock"] for p in response.json() if p["id"] == product)


def payload(client, product="rice", quantity=1):
    items = [{"id": product, "quantity": quantity}]
    quote = client.post("/api/catalog/quote", json={"items": items})
    assert quote.status_code == 200, quote.text
    return {
        "items": items,
        "expected_total": quote.json()["total"],
        "method": "mobile",
        "outcome": "success",
    }


def place(client, headers, body, key=None):
    return client.post(
        "/api/orders", headers={**headers, "Idempotency-Key": key or str(uuid4())}, json=body
    )


def test_profile_and_order_ownership(client):
    m, headers = merchant(client)
    assert client.get("/api/merchants/me", headers=headers).json()["id"] == m["id"]
    update = {k: v for k, v in m.items() if k != "id"}
    update["businessName"] = "Updated Shop"
    assert (
        client.put("/api/merchants/me", headers=headers, json=update).json()["businessName"]
        == "Updated Shop"
    )
    assert client.get("/api/orders").status_code == 401
    assert (
        client.get("/api/merchants/me", headers={"Authorization": "Bearer invalid"}).status_code
        == 401
    )
    result = place(client, headers, payload(client, "rice")).json()
    assert result["status"] == "confirmed", result
    _, other = merchant(client)
    assert client.get("/api/orders/" + result["id"], headers=other).status_code == 404
    assert client.get("/api/orders", headers=other).json() == []
    assert (
        client.get("/api/orders/" + result["id"], headers=headers).json()["total"]
        == result["total"]
    )


def test_decline_leaves_inventory_unchanged(client):
    _, headers = merchant(client)
    before = stock(client, "oil")
    body = payload(client, "oil")
    body["outcome"] = "declined"
    response = place(client, headers, body)
    assert response.json()["status"] == "declined", response.text
    assert stock(client, "oil") == before


def test_duplicate_concurrent_submissions_allocate_once(client):
    _, headers = merchant(client)
    before = stock(client, "tea")
    body = payload(client, "tea")
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: place(client, headers, body, key), range(4)))
    assert all(r.status_code in (200, 201) for r in results), [r.text for r in results]
    assert len({r.json()["id"] for r in results}) == 1
    assert all(r.json()["status"] == "confirmed" for r in results)
    assert stock(client, "tea") == before - 1
    changed = {**body, "method": "card"}
    assert place(client, headers, changed, key).status_code == 409


def test_stale_price_and_bad_inputs_do_not_allocate(client):
    _, headers = merchant(client)
    before = stock(client, "milk")
    body = payload(client, "milk")
    body["expected_total"] = 1
    response = place(client, headers, body)
    assert response.json()["status"] == "rejected", response.text
    assert stock(client, "milk") == before
    body["items"][0]["quantity"] = -1
    assert place(client, headers, body).status_code == 422
    assert (
        client.post(
            "/api/catalog/quote", json={"items": [{"id": "missing", "quantity": 1}]}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/catalog/quote", json={"items": [{"id": "rice", "quantity": 10000}]}
        ).status_code
        == 409
    )
    assert client.post("/api/internal/allocations/" + str(uuid4()), json={}).status_code == 404
    assert (
        client.post("/api/catalog/internal/allocations/" + str(uuid4()), json={}).status_code == 404
    )


def test_concurrent_buyers_cannot_oversell(client):
    before = stock(client, "tissue")
    assert before > 0, "Use a fresh disposable database for this inventory exhaustion test"
    body = payload(client, "tissue", before)
    auth = [merchant(client)[1], merchant(client)[1]]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda h: place(client, h, body).json(), auth))
    assert sorted(r["status"] for r in results) == ["confirmed", "rejected"], results
    assert stock(client, "tissue") == 0

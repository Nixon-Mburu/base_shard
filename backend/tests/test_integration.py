"""GraphQL contracts against a disposable seeded stack; consumes inventory."""

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest

from common.graphql_documents import DOCUMENTS

BASE = os.environ.get("TEST_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE, reason="Requires disposable stack")
PROFILE = {
    "businessName": "Integration Shop",
    "owner": "Test Merchant",
    "phone": "0712345678",
    "type": "Retail shop",
    "city": "Nairobi",
    "address": "Test Street",
    "point": {"lat": -1.28, "lng": 36.82},
}


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE or "http://unused", timeout=30, trust_env=False) as client:
        yield client


def gql(client, operation, variables=None, headers=None, error=None):
    response = client.post(
        "/graphql",
        json={"query": DOCUMENTS[operation], "variables": variables or {}},
        headers=headers or {},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    if error:
        assert result["errors"][0]["extensions"]["status"] == error, result
        return result
    assert not result.get("errors"), result
    return result["data"][operation]


def merchant(client):
    account = gql(client, "createMerchant", {"input": PROFILE})
    return account["merchant"], {"Authorization": "Bearer " + account["token"]}


def stock(client, product):
    return next(p["stock"] for p in gql(client, "products") if p["id"] == product)


def payload(client, product="rice", quantity=1):
    items = [{"id": product, "quantity": quantity}]
    quote = gql(client, "quote", {"input": {"items": items}})
    return {
        "items": items,
        "expectedTotal": quote["total"],
        "method": "mobile",
        "outcome": "success",
    }


def place(client, headers, body, key=None, error=None):
    return gql(
        client, "placeOrder", {"input": body, "idempotencyKey": key or str(uuid4())}, headers, error
    )


def test_profile_and_order_ownership(client):
    m, auth = merchant(client)
    assert gql(client, "me", headers=auth)["id"] == m["id"]
    assert (
        gql(client, "updateMerchant", {"input": {**PROFILE, "businessName": "Updated"}}, auth)[
            "businessName"
        ]
        == "Updated"
    )
    gql(client, "orders", error=401)
    gql(client, "me", headers={"Authorization": "Bearer invalid"}, error=401)
    order = place(client, auth, payload(client))
    assert order["status"] == "confirmed"
    _, other = merchant(client)
    gql(client, "order", {"id": order["id"]}, other, error=404)
    assert gql(client, "orders", headers=other) == []
    assert gql(client, "order", {"id": order["id"]}, auth)["total"] == order["total"]


def test_decline_preserves_stock(client):
    _, auth = merchant(client)
    before = stock(client, "oil")
    assert (
        place(client, auth, {**payload(client, "oil"), "outcome": "declined"})["status"]
        == "declined"
    )
    assert stock(client, "oil") == before


def test_concurrent_replay_allocates_once(client):
    _, auth = merchant(client)
    before = stock(client, "tea")
    body, key = payload(client, "tea"), str(uuid4())
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: place(client, auth, body, key), range(4)))
    assert len({r["id"] for r in results}) == 1
    assert all(r["status"] == "confirmed" for r in results)
    assert stock(client, "tea") == before - 1
    place(client, auth, {**body, "method": "card"}, key, error=409)


def test_validation_and_stale_price(client):
    _, auth = merchant(client)
    before = stock(client, "milk")
    body = payload(client, "milk")
    assert place(client, auth, {**body, "expectedTotal": 1})["status"] == "rejected"
    assert stock(client, "milk") == before
    body["items"][0]["quantity"] = -1
    place(client, auth, body, error=422)
    gql(client, "quote", {"input": {"items": [{"id": "missing", "quantity": 1}]}}, error=422)
    gql(client, "order", {"id": "not-a-uuid"}, auth, error=422)


def test_concurrent_buyers_cannot_oversell(client):
    before = stock(client, "tissue")
    assert 0 < before <= 10000, "Use a fresh disposable database"
    body = payload(client, "tissue", before)
    auth = [merchant(client)[1], merchant(client)[1]]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda h: place(client, h, body), auth))
    assert sorted(r["status"] for r in results) == ["confirmed", "rejected"]
    assert stock(client, "tissue") == 0


def test_schema_partial_data_aliases_and_private_operations(client):
    response = client.post(
        "/graphql",
        json={
            "query": "query { inventory: products { ...P } me { id } } fragment P on Product { id name }"
        },
    )
    result = response.json()
    assert result["data"]["inventory"]
    assert result["data"]["me"] is None
    assert result["errors"][0]["extensions"]["status"] == 401
    for query in [
        "{ products { unknownField } }",
        "mutation { allocateStock { total } }",
        "{ missing }",
    ]:
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 400
        assert "data" not in response.json()
    assert (
        client.get(
            "/graphql", params={"query": "mutation { createMerchant { token } }"}
        ).status_code
        == 405
    )

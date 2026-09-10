"""Optional crash-window recovery test against disposable local service databases."""

import os
import time
from uuid import uuid4

import httpx
import psycopg
import pytest
from psycopg.types.json import Jsonb

from common.graphql_documents import DOCUMENTS


def call(client, url, operation, variables=None, headers=None):
    response = client.post(
        url,
        json={"query": DOCUMENTS[operation], "variables": variables or {}},
        headers=headers or {},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert not result.get("errors"), result
    return result["data"][operation]


ORDERS_DB = os.environ.get("TEST_ORDERS_DATABASE_URL")
CATALOG = os.environ.get("TEST_CATALOG_URL")
BASE = os.environ.get("TEST_BASE_URL")
pytestmark = pytest.mark.skipif(
    not all([ORDERS_DB, CATALOG, BASE]), reason="Requires isolated service/database endpoints"
)


def test_recover_after_catalog_commit_before_order_confirmation():
    with httpx.Client(timeout=15, trust_env=False) as client:
        profile = {
            "businessName": "Recovery Shop",
            "owner": "Test",
            "phone": "0712345678",
            "type": "Shop",
            "city": "Nairobi",
            "address": "Test Street",
            "point": {"lat": -1.28, "lng": 36.82},
        }
        account = call(client, BASE + "/graphql", "createMerchant", {"input": profile})
        auth = {"Authorization": "Bearer " + account["token"]}
        items = [{"id": "soap", "quantity": 1}]
        quote = call(client, BASE + "/graphql", "quote", {"input": {"items": items}})
        before = next(
            p["stock"] for p in call(client, BASE + "/graphql", "products") if p["id"] == "soap"
        )
        order_id = uuid4()
        body = {"items": items, "expected_total": quote["total"]}
        variables = {
            "id": str(order_id),
            "input": {"items": items, "expectedTotal": quote["total"]},
        }
        denied = client.post(
            CATALOG + "/internal/graphql",
            json={"query": DOCUMENTS["allocateStock"], "variables": variables},
        )
        assert denied.status_code == 403
        call(
            client,
            CATALOG + "/internal/graphql",
            "allocateStock",
            variables,
            {"X-Service-Key": os.environ["TEST_SERVICE_KEY"]},
        )
        # Reproduce the durable state of a crash after catalog committed but
        # before the orders transaction recorded confirmation.
        with psycopg.connect(ORDERS_DB) as db:
            db.execute(
                "INSERT INTO orders(id,merchant_id,merchant,idempotency_key,request,status) VALUES (%s,%s,%s,%s,%s,'pending')",
                (
                    order_id,
                    account["merchant"]["id"],
                    Jsonb(account["merchant"]),
                    uuid4(),
                    Jsonb({**body, "method": "mobile", "outcome": "success"}),
                ),
            )
        for _ in range(40):
            order = call(client, BASE + "/graphql", "order", {"id": str(order_id)}, auth)
            if order["status"] == "confirmed":
                break
            time.sleep(0.25)
        assert order["status"] == "confirmed", order
        assert order["total"] == quote["total"]
        after = next(
            p["stock"] for p in call(client, BASE + "/graphql", "products") if p["id"] == "soap"
        )
        assert after == before - 1

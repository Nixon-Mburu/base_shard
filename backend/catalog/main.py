import json
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException
from psycopg.types.json import Jsonb

from common.db import connect, migrate
from common.graphql_api import allocation_input, mount
from common.http import add_database_errors, internal_access
from common.models import Allocation, Basket, calculate
from common.telemetry import configure


@asynccontextmanager
async def lifespan(_app):
    directory = Path(__file__).parent
    migrate(directory / "migrations")
    with connect() as db:
        for p in json.loads((directory / "seed.json").read_text()):
            db.execute(
                "INSERT INTO products(id,data,price,stock) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (p["id"], Jsonb(p), p["price"], p["stock"]),
            )
    yield


app = FastAPI(
    title="Base Grid Catalog & Inventory",
    lifespan=lifespan,
    docs_url="/api/catalog/docs",
    openapi_url="/api/catalog/openapi.json",
)
add_database_errors(app)
configure(app, "catalog")


def quote(db, basket, lock=False):
    ids = sorted(item.id for item in basket.items)
    rows = db.execute(
        "SELECT id,data,price,stock FROM products WHERE id=ANY(%s) ORDER BY id"
        + (" FOR UPDATE" if lock else ""),
        (ids,),
    ).fetchall()
    products = {row["id"]: row for row in rows}
    result = []
    for item in sorted(basket.items, key=lambda p: p.id):
        p = products.get(item.id)
        if p is None:
            raise HTTPException(422, f"Unknown product: {item.id}")
        if item.quantity > p["stock"]:
            raise HTTPException(
                409, f"Not enough stock for {p['data']['name']}; {p['stock']} available"
            )
        result.append(
            {
                **p["data"],
                "price": p["price"],
                "stock": p["stock"],
                "quantity": item.quantity,
            }
        )
    return calculate(result)


@app.get("/health")
def health():
    with connect() as db:
        db.execute("SELECT 1")
    return {"status": "ok", "service": "catalog"}


def products():
    with connect() as db:
        rows = db.execute("SELECT data,price,stock FROM products ORDER BY id").fetchall()
    return [{**p["data"], "price": p["price"], "stock": p["stock"]} for p in rows]


def get_quote(basket: Basket):
    with connect() as db:
        return quote(db, basket)


def allocate(allocation_id: UUID, payload: Allocation):
    body = payload.model_dump()
    with connect() as db:
        # Serialize duplicate requests before examining the durable allocation record.
        db.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
            (str(allocation_id),),
        )
        previous = db.execute(
            "SELECT request,result FROM allocations WHERE id=%s", (allocation_id,)
        ).fetchone()
        if previous:
            if previous["request"] != body:
                raise HTTPException(409, "Allocation ID was already used for another request")
            return previous["result"]
        result = quote(db, payload, lock=True)
        if result["total"] != payload.expected_total:
            raise HTTPException(409, "Prices changed. Review your order and try again.")
        for item in payload.items:
            db.execute(
                "UPDATE products SET stock=stock-%s WHERE id=%s",
                (item.quantity, item.id),
            )
        db.execute(
            "INSERT INTO allocations(id,request,result) VALUES (%s,%s,%s)",
            (allocation_id, Jsonb(body), Jsonb(result)),
        )
    return result


mount(
    app,
    {
        "products": lambda _, info: products(),
        "quote": lambda _, info, input: get_quote(Basket(**input)),
    },
)
mount(
    app,
    {},
    {
        "allocateStock": lambda _, info, input, id: allocate(
            UUID(id), Allocation(**allocation_input(input))
        )
    },
    path="/internal/graphql",
    authorize=lambda request: internal_access(request.headers.get("x-service-key", "")),
)

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Event, Thread
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from psycopg.types.json import Jsonb

from common.db import connect, migrate
from common.http import add_database_errors, merchant_session, request
from common.models import OrderRequest
from common.telemetry import configure

logger = logging.getLogger("base_grid.orders")


def serialize(row):
    return {
        **(row["summary"] or {}),
        "id": str(row["id"]),
        "merchant": row["merchant"],
        "method": row["request"]["method"],
        "status": row["status"],
        "error": row["error"],
        "createdAt": row["created_at"].isoformat(),
        "paymentSimulated": True,
        "deliveryStatus": "not_dispatched",
    }


def process(order_id):
    # Persist the intent before the remote call. If we crash after allocation, the
    # same order UUID retrieves that allocation without taking stock a second time.
    with connect() as db:
        row = db.execute("SELECT * FROM orders WHERE id=%s FOR UPDATE", (order_id,)).fetchone()
        if row["status"] != "pending":
            return serialize(row)
        payload = row["request"]
        try:
            summary = request(
                "POST",
                os.environ["CATALOG_URL"] + f"/internal/allocations/{order_id}",
                headers={"X-Service-Key": os.environ["SERVICE_KEY"]},
                json={
                    "items": payload["items"],
                    "expected_total": payload["expected_total"],
                },
            )
        except HTTPException as exc:
            if exc.status_code not in (409, 422):
                logger.warning(
                    "Order %s remains pending after service response %s", order_id, exc.status_code
                )
                # Timeouts are ambiguous. Leave pending and retry the SAME allocation.
                return serialize(row)
            row = db.execute(
                "UPDATE orders SET status='rejected', error=%s, updated_at=now() WHERE id=%s RETURNING *",
                (str(exc.detail), order_id),
            ).fetchone()
        else:
            row = db.execute(
                "UPDATE orders SET status='confirmed', summary=%s, updated_at=now() WHERE id=%s RETURNING *",
                (Jsonb(summary), order_id),
            ).fetchone()
        return serialize(row)


def recover(stop):
    while not stop.wait(3):
        try:
            with connect() as db:
                pending = db.execute(
                    "SELECT id FROM orders WHERE status='pending' ORDER BY created_at LIMIT 20"
                ).fetchall()
            for row in pending:
                if stop.is_set():
                    return
                process(row["id"])
        except Exception:
            logger.exception("Pending order recovery will retry")


@asynccontextmanager
async def lifespan(_app):
    migrate(Path(__file__).parent / "migrations")
    stop = Event()
    worker = Thread(target=recover, args=(stop,), daemon=True)
    worker.start()
    yield
    stop.set()
    worker.join(timeout=10)


app = FastAPI(
    title="Base Grid Orders",
    lifespan=lifespan,
    docs_url="/api/orders/docs",
    openapi_url="/api/orders/openapi.json",
)
add_database_errors(app)
configure(app, "orders")


@app.get("/health")
def health():
    with connect() as db:
        db.execute("SELECT 1")
    return {"status": "ok", "service": "orders"}


@app.post("/api/orders")
def create(
    payload: OrderRequest,
    response: Response,
    idempotency_key: UUID = Header(),
    merchant=Depends(merchant_session),
):
    body = payload.model_dump()
    body["items"] = sorted(body["items"], key=lambda item: item["id"])
    order_id = uuid4()
    # Simulated declines happen before inventory allocation. Nothing to release.
    declined = payload.outcome == "declined"
    with connect() as db:
        db.execute(
            """INSERT INTO orders(id,merchant_id,merchant,idempotency_key,request,status,error)
                   VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (merchant_id,idempotency_key) DO NOTHING""",
            (
                order_id,
                merchant["id"],
                Jsonb(merchant),
                idempotency_key,
                Jsonb(body),
                "declined" if declined else "pending",
                "The simulated payment was declined. Your basket is saved; try again."
                if declined
                else None,
            ),
        )
        row = db.execute(
            "SELECT * FROM orders WHERE merchant_id=%s AND idempotency_key=%s",
            (merchant["id"], idempotency_key),
        ).fetchone()
        if row["request"] != body:
            raise HTTPException(409, "Idempotency key was already used for another order")
    result = process(row["id"]) if row["status"] == "pending" else serialize(row)
    response.status_code = (
        202 if result["status"] == "pending" else (201 if row["id"] == order_id else 200)
    )
    return result


@app.get("/api/orders")
def list_orders(limit: int = Query(default=30, ge=1, le=100), merchant=Depends(merchant_session)):
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM orders WHERE merchant_id=%s ORDER BY created_at DESC LIMIT %s",
            (merchant["id"], limit),
        ).fetchall()
    return [serialize(row) for row in rows]


@app.get("/api/orders/{order_id}")
def get_order(order_id: UUID, merchant=Depends(merchant_session)):
    with connect() as db:
        row = db.execute(
            "SELECT * FROM orders WHERE id=%s AND merchant_id=%s",
            (order_id, merchant["id"]),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Order not found")
    return serialize(row)

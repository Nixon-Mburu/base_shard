# Backend services

Run the complete stack from the repository root with `docker compose up --build -d`. The frontend's Compose file includes `backend/compose.yaml`, so running the same command from `frontend/` works too.

## Public API

All paths are available through the public Nginx gateway on port 8080. API errors use a JSON `detail` field. Bodies reject unknown fields. Internal inventory endpoints are not exposed by either gateway.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/merchants` | Create profile; return `{merchant, token}` |
| GET | `/api/merchants/me` | Read the authenticated merchant |
| PUT | `/api/merchants/me` | Update the authenticated merchant |
| GET | `/api/catalog/products` | Current products/prices/available stock |
| POST | `/api/catalog/quote` | Validate quantities and calculate totals |
| POST | `/api/orders` | Place/resume an idempotent order |
| GET | `/api/orders?limit=30` | Authenticated merchant's recent orders (max 100) |
| GET | `/api/orders/{uuid}` | Read an owned order |

Interactive API docs: `/api/merchants/docs`, `/api/catalog/docs`, `/api/orders/docs`. Each service's `/health` checks its own database; container health checks call it directly. Gateway `/health` checks the gateway process.

Merchant profile:

```json
{
  "businessName": "Wanjiku Market",
  "owner": "Wanjiku",
  "phone": "0712345678",
  "type": "Retail shop",
  "city": "Nairobi",
  "address": "Moi Avenue, ground floor",
  "point": {"lat": -1.28, "lng": 36.82}
}
```

Authenticated requests require `Authorization: Bearer <token>`. The merchant ID is derived from the verified session, never accepted from an order body. There is no public list of merchants. Tokens are returned only on registration and stored hashed in the merchant database; the prototype browser session has no expiry/recovery flow yet.

Quote:

```json
{"items": [{"id": "rice", "quantity": 2}]}
```

Order creation requires a UUID `Idempotency-Key` header plus:

```json
{
  "items": [{"id": "rice", "quantity": 2}],
  "expected_total": 7250,
  "method": "mobile",
  "outcome": "success"
}
```

Use `method: "card"` for a simulated card payment and `outcome: "declined"` to exercise a decline. `expected_total` protects the merchant from changed prices; catalog calculates the authoritative total itself and rejects mismatches.

New terminal orders return 201; replayed terminal orders return 200; pending orders return 202. Inspect `status` (`pending`, `confirmed`, `declined`, `rejected`) even for a successful HTTP response. A terminal decline or rejection is a persisted order outcome. To place a new attempt after a terminal failure, send a new key. After a timeout or 503, retry the identical body with the **same key**. Reusing a key for a different body returns 409. Poll `GET /api/orders/{id}` while pending.

Confirmed order responses include product/price snapshots, quantity, subtotal, delivery, total, currency, merchant delivery snapshot, `paymentSimulated: true`, and `deliveryStatus: "not_dispatched"`.

## Storage and consistency

- `merchants/migrations`: merchant profiles and hashed session tokens.
- `catalog/migrations`: products and allocation records. Catalog seeds `seed.json` only for missing products.
- `orders/migrations`: merchant-owned orders, unique merchant/idempotency keys, pending-work index.
- Migrations run at service startup under a PostgreSQL advisory lock; each service tracks applied SQL filenames in its own database. Add a new numbered SQL migration for schema changes.
- Catalog allocation is one transaction. Ordered row locks prevent overselling and inconsistent multi-item allocation. A transaction-level advisory lock serializes repeated allocation IDs, including a retry arriving while the original request is still executing.
- Orders commits intent before making the catalog request. A recovery loop scans pending orders every three seconds. An ambiguous timeout never releases or duplicates stock: the same order ID returns the existing allocation. A 409/422 catalog rejection marks the order rejected. Other dependency failures remain pending and are logged for retry.
- There is no distributed transaction or real payment saga yet. Simulated declines happen before allocation; introducing real payments requires explicit authorization/capture and compensation behavior.

Each API uses only its own `DATABASE_URL`. Orders also needs `MERCHANTS_URL`, `CATALOG_URL`, and `SERVICE_KEY`. Catalog checks `SERVICE_KEY` for `POST /internal/allocations/{order_id}`; that endpoint is reachable only over the private container network and is absent from gateway routes. Ports are not published for databases or APIs in the default stack.

## Development and checks

Use the commands in the [root README](../README.md). Optional API-only Compose override: `compose.dev.yaml`, bound to loopback port 8088. Tests use real HTTP and PostgreSQL when integration environment variables are provided. Unit tests validate quantities, duplicate lines, coordinates, and delivery calculations without services.

Runtime dependencies are pinned in `requirements.txt`; testing/lint dependencies are in `requirements-dev.txt`. Each API image runs Uvicorn as an unprivileged user. Database volumes persist independently of API containers.

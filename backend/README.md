# GraphQL backend

The public endpoint is `POST /graphql`, routed through Nginx to the independently containerized `graphql-gateway`. It composes typed schemas from merchants, catalog and orders. Each service owns its PostgreSQL database. Both gateway delegation and service-to-service calls use GraphQL. `/health` remains an HTTP readiness endpoint.

Queries: `me`, `products`, `quote(input: BasketInput!)`, `orders(limit: Int = 30)`, `order(id: ID!)`.

Mutations: `createMerchant(input: MerchantInput!)`, `updateMerchant(input: MerchantInput!)`, `placeOrder(input: OrderInput!, idempotencyKey: ID!)`.

```graphql
query Browse {
  products { id name price stock }
}

mutation Submit($input: OrderInput!, $key: ID!) {
  placeOrder(input: $input, idempotencyKey: $key) {
    id status total error
  }
}
```

Order input contains `items: [{id, quantity}]`, `expectedTotal` (integer KES), `method` (`mobile` or `card`), and `outcome` (`success` or `declined`, simulated). Reuse the same UUID idempotency key and input after a timeout. Pending orders are recovered automatically; declined/rejected orders have nullable totals and empty items.

Signup returns `{ merchant, token }`. Send `Authorization: Bearer <token>` for profile updates and merchant-owned orders. Catalog queries and signup are public. Catalog's `/internal/graphql` exposes `allocateStock` only with `X-Service-Key`; this operation is absent from the public schema and Nginx routes.

GraphQL execution errors may accompany HTTP 200 and partial data. Always inspect `errors`, including `extensions.code` and `extensions.status`. Invalid documents return HTTP 400; GET is not supported. Query documents have size, token, depth and field limits. Client operation names, aliases, IDs and variables never become metric labels. Schemas support introspection; authoritative type definitions are in `common/graphql_api.py`, and reusable documents in `common/graphql_documents.py`.

REST business endpoints have been removed. No database migration or volume reset is needed. Rebuild the complete stack with `sudo docker compose up --build -d` from the repository root. The gateway is explicit schema composition, not Apollo Federation; new operations require a schema and resolver registration. Nginx balances gateway replicas and Docker service discovery resolves domain replicas.

Run `TEST_BASE_URL=http://localhost:18080 .venv/bin/pytest -q` from this directory against a fresh disposable stack. Integration tests consume inventory, including fully exhausting one product. The recovery test additionally uses `TEST_ORDERS_DATABASE_URL`, `TEST_CATALOG_URL`, and `TEST_SERVICE_KEY`.

# Base Grid frontend

A React shell and three independently built, runtime-loaded microfrontends. White page backgrounds, purple accents, and locally bundled Gabarito throughout.

## Run

```bash
# From frontend/; includes all backend services and databases.
sudo docker compose up --build -d
```

Open http://localhost:8080. The same command works at the repository root. See the [root README](../README.md) for configuration, API-only development, and database lifecycle details.

For local development, first start the backend stack, then:

```bash
npm ci
API_PROXY_TARGET=http://localhost:8080 npm run dev
```

Open http://localhost:5173. If using the API-only Compose dev override, use `API_PROXY_TARGET=http://localhost:8088`. Production bundle preview: `npm run build`, then `API_PROXY_TARGET=http://localhost:8088 npm run preview` (port 4173).

## Architecture

| App      | Shell route     | Standalone dev URL                  | Gateway standalone path |
| -------- | --------------- | ----------------------------------- | ----------------------- |
| Shell    | `/` → `/orders` | http://localhost:5173               | `/`                     |
| Signup   | `/signup`       | http://localhost:5174/mfe/signup/   | `/mfe/signup/`          |
| Orders   | `/orders`       | http://localhost:5175/mfe/orders/   | `/mfe/orders/`          |
| Checkout | `/checkout`     | http://localhost:5176/mfe/checkout/ | `/mfe/checkout/`        |

Each application has its own Dockerfile, package, `src/pages/` and `src/styles/`. The shell loads `/mfe/<app>/assets/remote.js` at runtime. Each remote exports `mount(element, {navigate})` and returns an unmount callback; it bundles React independently and has its own HTML entry point. Standalone pages render without shell chrome; use the shell for cross-page journeys.

The shell loads remote CSS separately and handles load failures with a retry action. Shared files are source-level contracts compiled into each app; rebuild affected apps after changing them. Rebuild a single app with `docker compose up -d --build orders`.

`shared/api.js` provides same-origin JSON requests, bearer-session headers, timeouts, readable API errors, product loading, and merchant saving. Both Vite and the production preview proxy `/graphql`; deployed traffic goes through the Nginx API gateway. No product prices or inventory are hardcoded in frontend source.

`shared/store.js` maintains basket quantities, the merchant/session cache, and pending order idempotency keys using `base-grid:*` localStorage keys and change events. This keeps state across remote mounts and reloads. Profiles, stock, orders and final totals are authoritative in the backend. Older frontend-only profiles must be saved once to create a server-side merchant.

## Flow

1. Enter business/contact details, select an OpenStreetMap delivery point, and save to the merchant API. Geolocation and manual coordinates are supported; Nairobi is the initial view.
2. Load products, search/filter/sort, and choose quantities within current displayed stock. The backend rechecks stock under concurrency.
3. Checkout obtains a fresh quote, then posts an order with a durable idempotency key. M-Pesa/card outcomes are simulated. Declines preserve the basket. Pending requests can be safely resumed after a response loss or reload.
4. Confirmation comes from the API and clears the basket. Recent orders are read from the orders service.

Fonts are served locally. Map tiles require internet access and show attribution; follow the [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/) and configure a suitable provider before significant production traffic. No geocoding/autocomplete API is used.

## Checks

```bash
npm test
npm run format:check
npm run build
npx playwright install chromium
BASE_URL=http://localhost:8080 npm run test:e2e
```

Browser tests require the real backend and consume demo stock. They cover signup, basket persistence, decline/retry, confirmation, mobile layout, and a lost order response recovered after reload without a duplicate order. Use a disposable test stack as described in the root README.

All remote apps use `shared/api.js` and typed documents in `shared/graphql.json`. The helper checks GraphQL errors even for HTTP 200. Checkout preserves persisted retry keys across reloads.

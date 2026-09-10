# Base Grid frontend

A merchant inventory storefront with a React shell and three independently built, runtime-loaded microfrontends. White page backgrounds, purple accents, and locally bundled Gabarito throughout.

## Run with Docker

From this directory:

```sh
docker compose up --build -d
```

Open http://localhost:8080. Set `FRONTEND_PORT=8081` if port 8080 is occupied. Docker daemon access is required. Check health with `docker compose ps`; stop with `docker compose down`.

Each app has its own Dockerfile and Node build stage, then serves static output using Nginx. Only the gateway publishes a host port. A page can be rebuilt independently:

```sh
docker compose up -d --build orders
```

The gateway resolves service addresses dynamically so it can follow replaced containers. JavaScript and HTML use revalidation to avoid serving stale remote entry points.

## Local development

Node 22 and npm are required.

```sh
npm ci
npm run dev
```

Open http://localhost:5173. The launcher runs all four Vite applications; the shell proxies the remote apps. Apps also run individually with `npm run dev --workspace=@base-grid/orders` (substitute the app name).

| Application         | Shell route                | Standalone development URL          | Gateway standalone path |
| ------------------- | -------------------------- | ----------------------------------- | ----------------------- |
| Shell               | `/` redirects to `/orders` | http://localhost:5173               | `/`                     |
| Merchant signup     | `/signup`                  | http://localhost:5174/mfe/signup/   | `/mfe/signup/`          |
| Inventory orders    | `/orders`                  | http://localhost:5175/mfe/orders/   | `/mfe/orders/`          |
| Summary and payment | `/checkout`                | http://localhost:5176/mfe/checkout/ | `/mfe/checkout/`        |

Standalone pages render without navigation chrome. Cross-page links require the shell origin; for a complete journey, use the shell or gateway.

For a local preview of the production bundles, run `npm run build` followed by `npm run preview`, then open http://localhost:4173. This preview server is for development; Docker uses Nginx.

## Architecture

```text
Browser → Nginx gateway :8080
             ├── /, /signup, /orders, /checkout → shell Nginx
             ├── /mfe/signup/*                  → signup Nginx
             ├── /mfe/orders/*                  → orders Nginx
             └── /mfe/checkout/*                → checkout Nginx
```

The shell owns navigation and loads each app's ES module at `/mfe/<app>/assets/remote.js`. Each module exposes `mount(element, { navigate })` and returns an unmount callback. Every remote bundles React independently and mounts its own root; there is no shared React context or build-time page import in the shell. The shell loads each remote's CSS separately and handles load failures with a retry action. Each app also includes an HTML entry point for standalone use.

```text
apps/
  shell/      src/pages/shell_page.jsx       src/styles/shell_page.css
  signup/     src/pages/signup_page.jsx      src/styles/signup_page.css
  orders/     src/pages/order_page.jsx       src/styles/order_page.css
  checkout/   src/pages/checkout_page.jsx    src/styles/checkout_page.css
shared/       catalog, browser store, product artwork, global typography/styles
nginx/        gateway and app server configurations
```

Shared files are source-level contracts compiled into each app. A shared-contract change requires rebuilding affected apps. The basket and merchant profile use versionless `base-grid:*` localStorage keys and `base-grid:change` events on the same origin; storage events update other tabs. Browser storage is for the demo, not an authenticated account or authoritative inventory service.

## User flow

1. Enter business/contact information, then place a delivery pin on OpenStreetMap. Browser geolocation and manual coordinates are available. Nairobi is the initial view; the city is editable.
2. Search and filter eight example wholesale products, sort by price, and adjust quantities up to demo stock limits. The basket persists through reloads and navigation.
3. Review quantities, delivery details and totals. Demo delivery costs KES 350, waived at KES 15,000. Prices are illustrative; no real tax calculation is performed.
4. Choose simulated M-Pesa or card payment. The outcome selector exercises success and decline; decline retains the basket. Success saves the latest demo order and clears the basket. No payment credentials are collected, no money is charged, and no delivery is dispatched.

Map tiles require internet access. Attribution is visible, and tile requests use the standard OSM endpoint with a browser referrer. No geocoding/autocomplete service is used. Follow the [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/) and configure a suitable tile provider before significant production traffic. Fonts are served locally and do not require Google Fonts.

## Verification

```sh
npm test
npm run build
npx playwright install chromium
npm run test:e2e
# Against the Docker deployment:
BASE_URL=http://localhost:8080 npm run test:e2e
docker compose config --quiet
```

Tests cover invalid basket data, stock bounds, pricing/delivery totals, merchant signup, basket persistence, payment decline/retry, successful order placement, catalog empty states and mobile overflow. Production browser testing should use the gateway to verify remote entries, CSS and deep-link fallback together.

Backend authentication, real inventory, persistent orders, payment processing and dispatch are future integrations.

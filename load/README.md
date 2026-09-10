# Kenya performance lab

Locust simulates merchant journeys over a seeded population of **100,000 synthetic merchants across all 47 Kenyan counties**. Names are plausible Kenyan name combinations, never a directory of actual people. Town names and coordinates come from GeoNames; see [source and license](data/SOURCES.md). Phone placeholders start with `000` and are not intended to be dialed. Locations are town reference points, not verified business addresses.

## View the dashboard

The Docker stack serves Grafana at **http://localhost:3000/d/base-grid-load**. Login: `admin` / `base-grid-local` (override with `GRAFANA_PASSWORD` before the first start).

During the current development session, a local validation instance is available at **http://localhost:13000/d/base-grid-load** with the same credentials. It stores actual API, Locust and PostgreSQL metrics from a bounded distributed smoke test. That local instance uses programs in `/tmp`, not Docker, and is not a durable startup mechanism. CPU/container-memory panels require cAdvisor with Docker access; absent metrics are not zero utilization.

## Start an isolated stack

Run from the repository root with Python 3.10+ and Docker Compose 2.20.3+:

```bash
python3 load/run.py --sudo up
python3 load/run.py --sudo seed
```

Omit `--sudo` if you have Docker access. The project name is fixed to `base-grid-load`: it uses its own databases/volumes and does not touch the normal frontend project. The API is on loopback port 18080; Grafana 3000; Prometheus 9090; Locust 8089 when a run is active. The load stack contains backend services, not the frontend containers.

Seeding runs outside the measured workload. It bulk-inserts deterministic fixture IDs into merchant PostgreSQL, writes a local account pool, and raises product stock to a 10-million-unit floor. It does not delete existing rows or reduce stock. Repeating seeding with the same population/secret is idempotent. Generated identities, account tokens, the seed secret, and result artifacts are ignored by Git. Protect `load/data/accounts.sqlite` as credentials even though this is a synthetic test environment.

## Compare API replicas

```bash
# Same workload, concurrency, database resources; change API replicas only.
python3 load/run.py --sudo run \
  --replicas 1,2,4 --users 100 --workers 2 \
  --spawn-rate 10 --warmup 30 --seconds 120
```

Each stage recreates API replicas and Locust workers, waits for the target concurrency, warms up, then measures. `--replicas` applies independently to merchants, orders and catalog. Nginx round-robin upstreams re-resolve Docker DNS addresses; the per-replica traffic panel verifies the requests are actually distributed. Each API replica gets 1 CPU/512 MiB and each PostgreSQL container 2 CPU/1 GiB by default; `API_CPUS` and `DB_CPUS` override CPU limits. This first experiment scales API processes **while keeping one database per service**. It does not shard or replicate PostgreSQL and does not geo-route by county.

Results are written under `load/results/<run-id>/`: Locust CSV/history, a run manifest (commit, population hash, hardware, concurrency, replicas and measurement window), and Prometheus query results. Measurement summaries exclude ramp-up and warm-up. Grafana annotations mark each measured interval. Select an experiment/time window to compare stages. Existing database/order history grows between stages; for rigorous experiments use an equivalently prepared fresh load database, repeat/reverse stage order, and record that distinction. The runner never deletes database volumes.

Profiles:

- `balanced`: browsing, profile reads, history, quotes and checkout; 2% simulated declines by default.
- `read-heavy`: mostly catalog reads, with a smaller checkout share.
- `hotspot`: the same journey mix with 80% of checkout choices directed at rice, stressing one inventory row. This is a product hotspot; generating a Nairobi-skewed population separately does not itself change routing.
- Signup writes: set `LOCUST_USER_CLASS=RegistrationMerchant` before a run. Registration is excluded from steady-state default measurements and adds new synthetic accounts.

To prepare a geographic skew manually, generate with `population.py --distribution hotspot` and run the fixture-seed service. National distribution is an explicit test weighting; hotspot allocates approximately 60% to Nairobi. Neither is a demographic estimate.

## 100,000 merchants vs concurrency

The cohort has 100,000 persistent identities; `--users` controls simultaneous virtual users. Each worker reads a disjoint index partition from SQLite, rotates merchant sessions every five actions, and reports distinct cohort accounts visited. Coverage is visible in Grafana. A short test will not necessarily visit all 100,000 merchants. Do not interpret dataset size as achieved concurrency or full population coverage.

Start small. Increase users gradually while checking generator CPU, failures, DB connections and p95/p99 latency. A 100,000-concurrent-user test typically needs multiple generator hosts and substantial system capacity; a laptop run cannot establish that capacity. Worker count must remain fixed during a stage because it defines account partitions. Restart master/workers to change it. FastHttpUser reduces generator overhead but does not remove CPU/network limits.

For a UI-controlled run, create `load/results/interactive`, start `locust-master` and the desired number of `locust-worker` replicas with the `load` profile, and ensure `LOAD_WORKERS` matches the worker count. Set the Locust target to `http://api-gateway`. Never point this workload at an unrelated external service.

## What is measured

| Measurement | Source | Meaning |
| --- | --- | --- |
| Client requests/sec, failures, p50/p95/p99 | Locust master aggregated from workers | Complete HTTP round-trip; semantic order rejections count as failures even with HTTP 201 |
| Server requests/sec and per-API latency | OpenTelemetry SDK → Collector → Prometheus | Includes internal HTTP requests; normalized route templates avoid UUID cardinality |
| Live replica count and load distribution | Per-instance OpenTelemetry resources/heartbeat | Docker hostname identifies each replica; heartbeat expiry excludes old replicas |
| DB CPU and container memory | cAdvisor → Prometheus | PostgreSQL container CPU in **cores**, not host CPU or fabricated SQL-derived CPU |
| Connections, limits, transactions, waits, size, cache hits | Read-only SQL exporters → Prometheus | Actual PostgreSQL statistics; exporter connections are included |
| Distributed traces | OpenTelemetry → Collector → Tempo | FastAPI, HTTPX and psycopg spans; sampled at 1% by default |
| County footprint / cohort coverage | Fixture metadata / worker reports | 47 aggregate geography labels; no merchant names, tokens or IDs in Prometheus labels |

The dashboard uses a light theme with purple styling and 33 panels/sections. Prometheus stores time series (30 days, capped at 10 GB); Grafana stores dashboard configuration/annotations; Tempo stores sampled traces (24 hours). These use persistent Docker volumes. Grafana does not itself store the request metrics. Exported trace parameters do not include credentials or merchant profile payloads. `TRACE_SAMPLE_RATIO` controls trace sampling; request metrics remain unsampled.

cAdvisor requires Linux Docker host access, privileged container execution and read-only host mounts. It is not a PostgreSQL exporter. If it cannot start, the CPU panels have no data and experiment reports flag incomplete telemetry. Co-locating generators, databases and monitoring competes for host resources; distribute generator hosts and hold monitoring/sampling settings constant for meaningful scaling comparisons.

## Tests and cleanup

```bash
python3 -m venv load/.venv
load/.venv/bin/pip install -r load/requirements.txt -r backend/requirements-dev.txt
cd load
.venv/bin/pytest -q
cd ..
docker compose -f load/compose.yaml config --quiet
python3 load/run.py --sudo down
```

Unit tests cover deterministic county coverage, profile validity, worker partitioning, dashboard query contracts and bounded telemetry labels. The local smoke validation seeded 100,000 merchants, used a Locust master plus two workers with 12 concurrent users, produced real Prometheus measurements, and stored traces in Tempo. It is a functional test, **not a full-capacity benchmark**. Docker-only cAdvisor metrics and the 1→2→4 Compose scaling sequence still need validation with host Docker permissions.

Configuration lives in `observability/`; regenerate the dashboard JSON with `python3 load/scripts/dashboard.py`. Avoid changing dashboards only in Grafana because provisioning is the source of truth. Stop/remove only the `base-grid-load` project. Do not add `down -v` unless you intend to permanently delete that project's benchmark data.

## GraphQL workload

All merchant traffic uses `POST /graphql`, with separate Locust names for `products`, `me`, `orders`, `quote`, `placeOrder`, `order`, and `createMerchant`. HTTP-200 GraphQL errors count as failures. Server latency panels group by canonical GraphQL root field (`operation`); the error ratio includes GraphQL execution errors. DB CPU and connection panels retain their existing sources.

The GraphQL gateway is a separate service with its own telemetry and resource limit. The default scaling experiment scales the three domain services while holding the gateway at one replica; gateway saturation can limit throughput. Compare its latency and CPU before attributing a plateau to databases. Scale gateway replicas separately when investigating that bottleneck. This change adds a network hop, so compare REST and GraphQL runs with distinct run IDs and equivalent workload settings.

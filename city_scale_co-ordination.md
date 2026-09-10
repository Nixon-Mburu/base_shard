# Base Grid — Distributed Inventory System

## Goal

Build a Base-inspired backend system to learn **scaling, database sharding, caching, concurrency, Kafka, distributed systems, and observability**.

Base coordinates inventory between merchants, suppliers, and warehouses. Merchants order products and Base determines where inventory should come from.

## Stack

* Python + FastAPI
* PostgreSQL
* Redis
* Kafka
* Docker
* React
* Prometheus + Grafana

## Core Entities

* Merchants
* Products
* Suppliers
* Warehouses
* Inventory
* Orders
* Order Items
* Deliveries
* Consumption Events

## Build Progression

### 1. Monolith

Build the entire working system using FastAPI and **one PostgreSQL database**.

Merchant → Order → Inventory Reservation → Warehouse → Delivery

### 2. Generate Scale

Create fake data for hundreds of thousands/millions of merchants, products, orders, and inventory records.

Use Locust or k6 to generate heavy traffic and measure p50/p95/p99 latency, throughput, DB CPU, connections, and slow queries.

### 3. Redis

Cache product catalogs, prices, warehouse availability, and other read-heavy data.

Handle TTLs, invalidation, cache stampedes, stale data, and hot keys.

### 4. Split Databases

Separate the system into databases for:

* Merchants
* Orders
* Inventory
* Catalog

Learn how the architecture changes when SQL JOINs can no longer cross everything.

### 5. Kafka

Make order processing event-driven.

```text
OrderCreated
      ↓
Kafka
 ├── Inventory Service
 ├── Procurement Service
 ├── Delivery Service
 └── Analytics Service
```

Handle retries, duplicate events, ordering, consumer groups, dead-letter queues, and idempotency.

### 6. Database Sharding

Shard merchant/order data across multiple PostgreSQL instances.

Start with:

```python
shard = hash(merchant_id) % shard_count
```

Build a shard router that automatically sends queries to the correct database.

Then increase the number of shards and observe the resharding problem.

Implement **consistent hashing and virtual nodes**.

### 7. Geographic Sharding

Model Base operating across:

```text
Kenya
├── Nairobi
├── Mombasa
├── Kisumu
├── Nakuru
└── Eldoret
```

Experiment with geographic shards and then deliberately create a **hot-shard problem** where Nairobi receives most traffic.

Design a strategy for splitting Nairobi further.

### 8. Replication

Give shards read replicas.

Writes → Primary
Reads → Replicas

Simulate replication lag and implement read-your-writes behavior where necessary.

### 9. Inventory Concurrency

Simulate thousands of restaurants purchasing the same limited inventory simultaneously.

Prevent overselling using and comparing:

* atomic SQL updates
* optimistic locking
* `SELECT FOR UPDATE`
* reservation ledgers

### 10. Distributed Transactions

An order can involve:

```text
Order
→ Reserve Inventory
→ Select Supplier
→ Authorize Payment
→ Schedule Delivery
```

Implement a **Saga** with compensating actions when one step fails.

### 11. Replenishment Engine

Track merchant consumption and calculate when inventory will run out.

```text
Consumption Events
        ↓
Demand Estimate
        ↓
Current Inventory
        ↓
Reorder Point
        ↓
Replenishment Recommendation
```

### 12. Observability

Build a Base Ops dashboard showing:

```text
Requests/sec
Orders/sec
p99 latency
DB utilization
cache hit rate
Kafka lag
hot shards
replication lag
inventory events/sec
```

Use Prometheus, Grafana, and OpenTelemetry.

## Critical Rule

**Do not build the distributed architecture immediately.**

Build sequentially:

```text
Monolith
→ Load Test
→ Find Bottleneck
→ Optimize
→ Cache
→ Replicate
→ Kafka
→ Shard
→ Reshard
→ Handle Hot Shards
→ Distributed Transactions
→ Observability
```

At every stage, deliberately load-test the system until it breaks, identify **why it broke**, implement the next scaling mechanism, and measure whether the change actually improved performance.

The objective is not simply to build Base. The objective is to understand **why and when a system needs each distributed-systems technique**.

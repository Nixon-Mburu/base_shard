"""Read-only PostgreSQL observation; CPU comes separately from cAdvisor."""

import os
import time

import psycopg
from prometheus_client import CollectorRegistry, start_http_server
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily


class DatabaseCollector:
    def collect(self):
        service = os.environ["DB_SERVICE"]
        labels = ["service"]
        start = time.perf_counter()
        ok = 0
        try:
            with psycopg.connect(
                os.environ["DATABASE_URL"],
                connect_timeout=2,
                options="-c default_transaction_read_only=on -c statement_timeout=2000",
            ) as db:
                limit = int(db.execute("SHOW max_connections").fetchone()[0])
                states = db.execute(
                    "SELECT coalesce(state,'unknown'),count(*) FROM pg_stat_activity WHERE datname=current_database() GROUP BY state"
                ).fetchall()
                row = db.execute(
                    "SELECT xact_commit,xact_rollback,deadlocks,blks_hit,blks_read FROM pg_stat_database WHERE datname=current_database()"
                ).fetchone()
                waiters = db.execute(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock'"
                ).fetchone()[0]
                size = db.execute("SELECT pg_database_size(current_database())").fetchone()[0]
                oldest = db.execute(
                    "SELECT coalesce(max(extract(epoch FROM now()-xact_start)),0) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()"
                ).fetchone()[0]
            connection = GaugeMetricFamily(
                "base_db_connections",
                "Connections by PostgreSQL state",
                labels=["service", "state"],
            )
            values = dict(states)
            for state in (
                "active",
                "idle",
                "idle in transaction",
                "idle in transaction (aborted)",
                "disabled",
                "unknown",
            ):
                connection.add_metric([service, state], values.get(state, 0))
            yield connection
            for name, value in [
                ("base_db_connection_limit", limit),
                ("base_db_lock_waiters", waiters),
                ("base_db_size_bytes", size),
                ("base_db_oldest_transaction_seconds", float(oldest)),
            ]:
                metric = GaugeMetricFamily(name, name, labels=labels)
                metric.add_metric([service], value)
                yield metric
            for name, value in zip(
                [
                    "base_db_commits",
                    "base_db_rollbacks",
                    "base_db_deadlocks",
                    "base_db_cache_hits",
                    "base_db_disk_reads",
                ],
                row,
            ):
                metric = CounterMetricFamily(name, name, labels=labels)
                metric.add_metric([service], value)
                yield metric
            ok = 1
        except psycopg.Error:
            pass  # Scrape health exposes failure; do not fabricate zero connections/CPU.
        healthy = GaugeMetricFamily(
            "base_db_scrape_success",
            "Database metrics collection succeeded",
            labels=labels,
        )
        healthy.add_metric([service], ok)
        yield healthy
        elapsed = GaugeMetricFamily(
            "base_db_scrape_duration_seconds", "Exporter query duration", labels=labels
        )
        elapsed.add_metric([service], time.perf_counter() - start)
        yield elapsed


if __name__ == "__main__":
    registry = CollectorRegistry()
    registry.register(DatabaseCollector())
    start_http_server(int(os.environ.get("METRICS_PORT", "9187")), registry=registry)
    while True:
        time.sleep(60)

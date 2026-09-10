"""Master aggregates Locust worker statistics; metrics contain no merchant identifiers."""

import json
import os
from pathlib import Path

from prometheus_client.core import (
    CounterMetricFamily,
    GaugeMetricFamily,
    HistogramMetricFamily,
)

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 40)


class LocustCollector:
    def __init__(self, environment):
        self.environment = environment
        path = Path(os.environ.get("POPULATION_MANIFEST", "/data/population-manifest.json"))
        self.population = json.loads(path.read_text()) if path.exists() else {}
        self.locations = json.loads((Path(__file__).parent / "data/locations.json").read_text())

    def collect(self):
        env = self.environment
        runner = env.runner
        run_id = os.environ.get("RUN_ID", "interactive")
        labels = ["run_id"]
        for name, value in [
            ("load_active_users", runner.user_count),
            ("load_workers", len(runner.clients) if hasattr(runner, "clients") else 1),
            (
                "load_merchants_visited",
                sum(x.get("visited", 0) for x in env.load_reports.values()),
            ),
        ]:
            metric = GaugeMetricFamily(name, name, labels=labels)
            metric.add_metric([run_id], value)
            yield metric
        population = GaugeMetricFamily("load_population", "Synthetic cohort size")
        population.add_metric([], self.population.get("count", 0))
        yield population
        geography = GaugeMetricFamily(
            "load_population_county",
            "Cohort size per county",
            labels=["county", "latitude", "longitude"],
        )
        for county, count in self.population.get("counties", {}).items():
            point = next(p for p in self.locations if p["county"] == county)
            geography.add_metric([county, str(point["lat"]), str(point["lng"])], count)
        yield geography
        requests = CounterMetricFamily(
            "load_requests",
            "All client-observed requests",
            labels=["run_id", "method", "route"],
        )
        failures = CounterMetricFamily(
            "load_failures",
            "Transport, HTTP and semantic failures",
            labels=["run_id", "method", "route"],
        )
        duration = HistogramMetricFamily(
            "load_response_seconds",
            "End-to-end client response distribution",
            labels=["run_id", "method", "route"],
        )
        for entry in list(env.stats.entries.values()):
            values = [run_id, entry.method, entry.name]
            requests.add_metric(values, entry.num_requests)
            failures.add_metric(values, entry.num_failures)
            frequencies = list(entry.response_times.items())
            buckets = [
                (
                    str(b),
                    sum(n for milliseconds, n in frequencies if milliseconds <= b * 1000),
                )
                for b in BUCKETS
            ]
            buckets.append(("+Inf", sum(n for _, n in frequencies)))
            duration.add_metric(values, buckets, entry.total_response_time / 1000)
        yield requests
        yield failures
        yield duration
        outcomes = CounterMetricFamily(
            "load_order_outcomes",
            "Observed order outcomes",
            labels=["run_id", "outcome"],
        )
        for state in ["confirmed", "declined", "rejected", "pending"]:
            outcomes.add_metric(
                [run_id, state],
                sum(x.get("outcomes", {}).get(state, 0) for x in env.load_reports.values()),
            )
        yield outcomes
        cpu = GaugeMetricFamily(
            "load_worker_cpu_ratio",
            "Load generator CPU; one core equals 1",
            labels=["run_id", "worker"],
        )
        if hasattr(runner, "clients"):
            for worker in runner.clients.values():
                cpu.add_metric([run_id, worker.id], worker.cpu_usage / 100)
        else:
            cpu.add_metric([run_id, "local"], runner.current_cpu_usage / 100)
        yield cpu

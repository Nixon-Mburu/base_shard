"""Generate the provisioned Grafana dashboard; all queries are versioned in source."""

import json
from pathlib import Path

API = '{service_name=~"$service",benchmark_run_id=~"$run_id"}'
CLIENT = '{run_id=~"$run_id"}'
CONTAINERS = '{container_label_com_docker_compose_project="base-grid-load"}'
DBCPU = '{container_label_com_docker_compose_project="base-grid-load",container_label_com_docker_compose_service=~".*-db"}'
PANELS = []


def panel(
    title,
    expr,
    x,
    y,
    w=12,
    h=8,
    kind="timeseries",
    unit="short",
    description="",
    legend="{{service_name}}",
):
    p = {
        "id": len(PANELS) + 1,
        "type": kind,
        "title": title,
        "description": description,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "targets": [{"refId": "A", "expr": expr, "legendFormat": legend}],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "color": {"mode": "palette-classic"},
                "custom": {"lineWidth": 2, "fillOpacity": 12, "showPoints": "never"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "purple", "value": None}],
                },
            },
            "overrides": [],
        },
        "options": {
            "tooltip": {"mode": "multi"},
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "calcs": ["lastNotNull", "max"],
            },
        },
    }
    if kind == "stat":
        p["options"] = {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "colorMode": "value",
            "graphMode": "area",
            "textMode": "auto",
        }
        p["fieldConfig"]["defaults"]["color"] = {
            "mode": "fixed",
            "fixedColor": "purple",
        }
    PANELS.append(p)
    return p


def row(title, y):
    PANELS.append(
        {
            "id": len(PANELS) + 1,
            "type": "row",
            "title": title,
            "collapsed": False,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1},
            "panels": [],
        }
    )


def build():
    PANELS.clear()
    PANELS.append(
        {
            "id": 1,
            "type": "text",
            "title": "BASE GRID  /  KENYA PERFORMANCE LAB",
            "gridPos": {"x": 0, "y": 0, "w": 24, "h": 3},
            "options": {
                "mode": "markdown",
                "content": "### From one replica to a distributed platform\n**100,000 synthetic merchants · 47 Kenyan counties · One measurable journey**\nClient throughput → API latency → database pressure. Select a run and service, then compare the same time window. Purple = throughput, amber/red = pressure. Missing data means an unavailable source, never zero load.",
            },
        }
    )
    stats = [
        ("Merchant population", "max(load_population)", "short"),
        ("Active users", "sum(load_active_users" + CLIENT + ")", "short"),
        (
            "Client requests / sec",
            "sum(rate(load_requests_total" + CLIENT + "[$__rate_interval]))",
            "reqps",
        ),
        (
            "Client p95",
            "histogram_quantile(.95,sum by(le)(rate(load_response_seconds_bucket"
            + CLIENT
            + "[$__rate_interval])))",
            "s",
        ),
        (
            "Client failures",
            "sum(rate(load_failures_total"
            + CLIENT
            + "[$__rate_interval])) / clamp_min(sum(rate(load_requests_total"
            + CLIENT
            + "[$__rate_interval])), .001)",
            "percentunit",
        ),
        (
            "Live API replicas",
            "count(base_api_heartbeat" + API + " > (time()-30))",
            "short",
        ),
    ]
    for i, (title, q, unit) in enumerate(stats):
        panel(title, q, i * 4, 3, w=4, h=4, kind="stat", unit=unit)
    row("01   TRAFFIC & USER EXPERIENCE", 7)
    panel(
        "Client throughput · all workers",
        "sum by(method,route)(rate(load_requests_total" + CLIENT + "[$__rate_interval]))",
        0,
        8,
        unit="reqps",
        legend="{{method}} {{route}}",
        description="Locust client requests; not multiplied by internal service calls.",
    )
    p = panel(
        "Client response time · p50 / p95 / p99",
        "",
        12,
        8,
        unit="s",
        description="End-to-end response including gateway and network, estimated from Locust rounded response-time histograms.",
    )
    p["targets"] = [
        {
            "refId": chr(65 + i),
            "expr": f"histogram_quantile({q},sum by(le)(rate(load_response_seconds_bucket"
            + CLIENT
            + "[$__rate_interval])))",
            "legendFormat": label,
        }
        for i, (q, label) in enumerate([(0.5, "p50"), (0.95, "p95"), (0.99, "p99")])
    ]
    panel(
        "Active merchants in flight",
        "sum(load_active_users" + CLIENT + ")",
        0,
        16,
        w=8,
        unit="short",
        legend="Active virtual users",
    )
    panel(
        "Unique cohort merchants visited",
        "sum(load_merchants_visited" + CLIENT + ")",
        8,
        16,
        w=8,
        legend="Distinct accounts visited",
        description="Workers use disjoint index partitions; count covers selected cohort accounts, not 100,000 concurrent users.",
    )
    panel(
        "Confirmed / declined / rejected orders",
        "sum by(outcome)(rate(load_order_outcomes_total" + CLIENT + "[$__rate_interval]))",
        16,
        16,
        w=8,
        unit="ops",
        legend="{{outcome}}",
        description="Declines are expected simulated outcomes. Rejected orders count as client semantic failures. Pending records count once on first observation.",
    )
    row("02   API SERVICES · REPLICA-AWARE", 24)
    panel(
        "Server requests / sec",
        "sum by(service_name)(rate(base_api_requests_total" + API + "[$__rate_interval]))",
        0,
        25,
        unit="reqps",
        description="Includes internal service requests. Do not add to Locust RPS.",
    )
    panel(
        "Server p95 by endpoint",
        "histogram_quantile(.95,sum by(le,service_name,route)(rate(base_api_duration_seconds_bucket"
        + API
        + "[$__rate_interval])))",
        12,
        25,
        unit="s",
        legend="{{service_name}} · {{route}}",
    )
    panel(
        "Load distribution across replicas",
        "sum by(service_name,service_instance_id)(rate(base_api_requests_total"
        + API
        + "[$__rate_interval]))",
        0,
        33,
        unit="reqps",
        legend="{{service_name}} / {{service_instance_id}}",
        description="Use this to verify Nginx actually distributes traffic after scaling.",
    )
    panel(
        "Server 5xx ratio",
        'sum by(service_name)(rate(base_api_requests_total{service_name=~"$service",benchmark_run_id=~"$run_id",status=~"5.."}[$__rate_interval])) / clamp_min(sum by(service_name)(rate(base_api_requests_total'
        + API
        + "[$__rate_interval])),.001)",
        12,
        33,
        unit="percentunit",
    )
    table = panel(
        "Per-API response time · p50 / p95 / p99",
        "",
        0,
        41,
        w=24,
        h=9,
        kind="table",
        unit="s",
    )
    table["targets"] = [
        {
            "refId": label,
            "expr": f"histogram_quantile({q},sum by(le,service_name,method,route)(rate(base_api_duration_seconds_bucket"
            + API
            + "[$__rate_interval])))",
            "format": "table",
            "instant": True,
        }
        for q, label in [(0.5, "p50"), (0.95, "p95"), (0.99, "p99")]
    ]
    table["transformations"] = [{"id": "merge", "options": {}}]
    row("03   POSTGRESQL · WHERE DOES PRESSURE MOVE?", 50)
    panel(
        "Database CPU · cores consumed",
        "sum by(container_label_com_docker_compose_service)(rate(container_cpu_usage_seconds_total"
        + DBCPU
        + "[$__rate_interval]))",
        0,
        51,
        unit="cores",
        legend="{{container_label_com_docker_compose_service}}",
        description="Measured by cAdvisor from PostgreSQL containers. 1.0 = one fully used CPU core. Not pg_stat_database and not host CPU.",
    )
    panel(
        "Database connections / capacity",
        "sum by(service)(base_db_connections)",
        12,
        51,
        legend="{{service}} connections",
    )
    PANELS[-1]["targets"].append(
        {
            "refId": "B",
            "expr": "base_db_connection_limit",
            "legendFormat": "{{service}} limit",
        }
    )
    panel(
        "Connections by state",
        "base_db_connections",
        0,
        59,
        w=8,
        legend="{{service}} / {{state}}",
    )
    panel("Lock waiters", "base_db_lock_waiters", 8, 59, w=8, legend="{{service}}")
    panel(
        "Longest open transaction",
        "base_db_oldest_transaction_seconds",
        16,
        59,
        w=8,
        unit="s",
        legend="{{service}}",
    )
    panel(
        "Commits & rollbacks / sec",
        "rate(base_db_commits_total[$__rate_interval])",
        0,
        67,
        w=8,
        unit="ops",
        legend="{{service}} commits",
    )
    PANELS[-1]["targets"].append(
        {
            "refId": "B",
            "expr": "rate(base_db_rollbacks_total[$__rate_interval])",
            "legendFormat": "{{service}} rollbacks",
        }
    )
    panel(
        "Buffer cache hit ratio",
        "rate(base_db_cache_hits_total[$__rate_interval]) / clamp_min(rate(base_db_cache_hits_total[$__rate_interval])+rate(base_db_disk_reads_total[$__rate_interval]),.001)",
        8,
        67,
        w=8,
        unit="percentunit",
        legend="{{service}}",
    )
    panel(
        "Database size",
        "base_db_size_bytes",
        16,
        67,
        w=8,
        unit="bytes",
        legend="{{service}}",
    )
    row("04   KENYA COHORT & TEST VALIDITY", 75)
    geo = panel(
        "Merchant footprint · all 47 counties",
        "load_population_county",
        0,
        76,
        w=12,
        h=12,
        kind="geomap",
    )
    geo["targets"][0].update({"instant": True, "format": "table"})
    geo["transformations"] = [
        {
            "id": "convertFieldType",
            "options": {
                "conversions": [
                    {"targetField": "latitude", "destinationType": "number"},
                    {"targetField": "longitude", "destinationType": "number"},
                ]
            },
        }
    ]
    geo["options"] = {
        "view": {"id": "coords", "lat": 0.2, "lon": 37.7, "zoom": 5},
        "basemap": {"type": "default", "name": "OpenStreetMap"},
        "controls": {"showZoom": True, "showAttribution": True},
        "layers": [
            {
                "type": "markers",
                "name": "County population",
                "location": {
                    "mode": "coords",
                    "latitude": "latitude",
                    "longitude": "longitude",
                },
                "config": {
                    "showLegend": True,
                    "style": {
                        "color": {"fixed": "purple"},
                        "size": {"field": "Value", "fixed": 8, "min": 4, "max": 25},
                        "opacity": 0.75,
                    },
                },
            }
        ],
    }
    panel(
        "Generator CPU · watch before blaming the API",
        "load_worker_cpu_ratio" + CLIENT,
        12,
        76,
        h=6,
        unit="percentunit",
        legend="{{worker}}",
        description="85%+ sustained on a worker suggests load-generator saturation. Add workers or use separate hosts.",
    )
    panel(
        "Database telemetry health",
        "base_db_scrape_success",
        12,
        82,
        h=6,
        kind="stat",
        legend="{{service}}",
        description="1 = collecting; 0 = failed. CPU panels also require cAdvisor host permissions.",
    )
    panel(
        "Application, database & generator memory",
        "sum by(container_label_com_docker_compose_service)(container_memory_working_set_bytes"
        + CONTAINERS
        + ")",
        0,
        88,
        w=24,
        unit="bytes",
        legend="{{container_label_com_docker_compose_service}}",
    )
    return {
        "uid": "base-grid-load",
        "title": "Base Grid · Kenya Performance Lab",
        "tags": ["base-grid", "locust", "kenya", "scaling"],
        "timezone": "browser",
        "schemaVersion": 40,
        "version": 1,
        "refresh": "5s",
        "time": {"from": "now-30m", "to": "now"},
        "editable": False,
        "graphTooltip": 1,
        "links": [
            {
                "title": "Explore distributed traces",
                "type": "link",
                "url": '/explore?left={"datasource":"tempo","queries":[{"queryType":"traceql","query":"{resource.service.name != ""}"}]}',
                "targetBlank": True,
            }
        ],
        "templating": {
            "list": [
                {
                    "name": "run_id",
                    "label": "Experiment",
                    "type": "query",
                    "datasource": {"uid": "prometheus", "type": "prometheus"},
                    "query": "label_values(load_active_users, run_id)",
                    "includeAll": True,
                    "allValue": ".*",
                    "multi": False,
                    "refresh": 1,
                    "current": {"text": "All", "value": "$__all"},
                },
                {
                    "name": "service",
                    "label": "API service",
                    "type": "query",
                    "datasource": {"uid": "prometheus", "type": "prometheus"},
                    "query": "label_values(base_api_requests_total, service_name)",
                    "includeAll": True,
                    "allValue": ".*",
                    "multi": True,
                    "refresh": 1,
                    "current": {"text": "All", "value": "$__all"},
                },
            ]
        },
        "annotations": {
            "list": [
                {
                    "name": "Experiment runs",
                    "type": "dashboard",
                    "builtIn": 1,
                    "enable": True,
                    "hide": False,
                    "iconColor": "#9b6bed",
                }
            ]
        },
        "panels": PANELS,
    }


if __name__ == "__main__":
    target = Path(__file__).parents[1] / "observability/grafana/dashboards/base-grid.json"
    target.write_text(json.dumps(build(), indent=2) + "\n")
    print(f"Wrote {len(PANELS)} panels to {target}")

"""Repeatable Docker Compose experiments; no destructive volume reset operations."""

import argparse
import base64
import json
import os
import platform
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


def http(url, data=None, method=None, auth=None):
    body = urlencode(data).encode() if data is not None else None
    headers = {}
    if auth:
        headers["Authorization"] = "Basic " + base64.b64encode(auth.encode()).decode()
    with urlopen(Request(url, data=body, method=method, headers=headers), timeout=20) as response:
        return json.load(response)


def compose(args, env, sudo=False, capture=False):
    command = (
        (["sudo"] if sudo else [])
        + [
            "docker",
            "compose",
            "--project-name",
            "base-grid-load",
            "--file",
            str(ROOT / "compose.yaml"),
            "--profile",
            "load",
        ]
        + args
    )
    return subprocess.run(
        command,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    ).stdout


def wait_for(predicate, timeout, message):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except (URLError, ValueError, KeyError):
            pass
        time.sleep(2)
    raise RuntimeError(message)


def annotation(grafana, run_id, start, end):
    payload = json.dumps(
        {
            "dashboardUID": "base-grid-load",
            "time": int(start * 1000),
            "timeEnd": int(end * 1000),
            "tags": ["benchmark", run_id],
            "text": run_id,
        }
    ).encode()
    auth = base64.b64encode(
        ("admin:" + os.environ.get("GRAFANA_PASSWORD", "base-grid-local")).encode()
    ).decode()
    request = Request(
        grafana + "/api/annotations",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Basic " + auth},
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def summarize(prometheus, run_id, start, end):
    seconds = max(10, int(end - start))
    window = f"{seconds}s"
    client = '{run_id="' + run_id + '"}'
    api = '{benchmark_run_id="' + run_id + '"}'
    queries = {
        "client_requests": "sum(increase(load_requests_total" + client + "[" + window + "]))",
        "client_rps": "sum(increase(load_requests_total"
        + client
        + "["
        + window
        + "]))/"
        + str(seconds),
        "client_failure_ratio": "sum(increase(load_failures_total"
        + client
        + "["
        + window
        + "])) / clamp_min(sum(increase(load_requests_total"
        + client
        + "["
        + window
        + "])),1)",
        "client_p95_seconds": "histogram_quantile(.95,sum by(le)(increase(load_response_seconds_bucket"
        + client
        + "["
        + window
        + "])))",
        "api_p95_seconds": "histogram_quantile(.95,sum by(le,service_name,route)(increase(base_api_duration_seconds_bucket"
        + api
        + "["
        + window
        + "])))",
        "api_rps": "sum by(service_name)(increase(base_api_requests_total"
        + api
        + "["
        + window
        + "]))/"
        + str(seconds),
        "db_connections_peak": "max_over_time((sum by(service)(base_db_connections))["
        + window
        + ":5s])",
        "db_cpu_cores_mean": 'avg_over_time((sum by(container_label_com_docker_compose_service)(rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_project="base-grid-load",container_label_com_docker_compose_service=~".*-db"}[30s])))['
        + window
        + ":5s])",
        "worker_cpu_peak": "max_over_time(load_worker_cpu_ratio" + client + "[" + window + "])",
        "merchants_visited": "sum(load_merchants_visited" + client + ")",
    }
    result = {}
    for name, query in queries.items():
        try:
            result[name] = http(
                prometheus + "/api/v1/query?" + urlencode({"query": query, "time": end})
            )
        except (URLError, ValueError) as e:
            result[name] = {"error": str(e)}
    return result


def experiment(args, replicas, env):
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + f"-r{replicas}-u{args.users}-{args.workload}"
    )
    env = {
        **env,
        "RUN_ID": run_id,
        "LOAD_WORKERS": str(args.workers),
        "WORKLOAD": args.workload,
    }
    output = ROOT / "results" / run_id
    output.mkdir(parents=True)
    locust = "http://127.0.0.1:" + env.get("LOCUST_PORT", "8089")
    prometheus = "http://127.0.0.1:" + env.get("PROMETHEUS_PORT", "9090")
    grafana = "http://127.0.0.1:" + env.get("GRAFANA_PORT", "3000")
    manifest = {
        "run_id": run_id,
        "replicas_per_api": replicas,
        "users": args.users,
        "workers": args.workers,
        "spawn_rate": args.spawn_rate,
        "warmup_seconds": args.warmup,
        "measured_seconds": args.seconds,
        "workload": args.workload,
        "api_cpus_per_replica": env.get("API_CPUS", "1"),
        "db_cpus_each": env.get("DB_CPUS", "2"),
        "trace_sample_ratio": env.get("TRACE_SAMPLE_RATIO", ".01"),
        "host": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "population": json.loads((ROOT / "data/population-manifest.json").read_text()),
        "status": "starting",
    }
    manifest["commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    ).stdout.strip()
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    try:
        compose(["stop", "locust-worker", "locust-master"], env, args.sudo)
        compose(["rm", "-f", "locust-worker", "locust-master"], env, args.sudo)
        scale = [
            part
            for service in ("merchants-api", "catalog-api", "orders-api")
            for part in ("--scale", f"{service}={replicas}")
        ]
        compose(
            [
                "up",
                "-d",
                "--no-deps",
                "--force-recreate",
                *scale,
                "merchants-api",
                "catalog-api",
                "orders-api",
            ],
            env,
            args.sudo,
        )
        wait_for(
            lambda: http(
                "http://127.0.0.1:" + env.get("LOAD_API_PORT", "18080") + "/api/catalog/products"
            ),
            90,
            "API services did not become ready",
        )
        compose(
            [
                "up",
                "-d",
                "--no-deps",
                "--scale",
                f"locust-worker={args.workers}",
                "locust-master",
                "locust-worker",
            ],
            env,
            args.sudo,
        )
        wait_for(
            lambda: len(http(locust + "/stats/requests").get("workers", [])) == args.workers,
            90,
            "Not all Locust workers connected",
        )
        http(
            locust + "/swarm",
            {
                "user_count": args.users,
                "spawn_rate": args.spawn_rate,
                "host": "http://api-gateway",
            },
        )
        wait_for(
            lambda: http(locust + "/stats/requests")["user_count"] == args.users,
            max(90, args.users / args.spawn_rate * 2),
            "Target concurrency was not reached",
        )
        print(f"{run_id}: warmup {args.warmup}s, measurement {args.seconds}s", flush=True)
        time.sleep(args.warmup)
        start = time.time()
        time.sleep(args.seconds)
        end = time.time()
        # Allow cumulative exports to land before querying the measured historical window.
        time.sleep(10)
        results = summarize(prometheus, run_id, start, end)
        (output / "prometheus-summary.json").write_text(json.dumps(results, indent=2))
        missing = [
            k
            for k, v in results.items()
            if v.get("status") != "success" or not v.get("data", {}).get("result")
        ]
        manifest.update(
            status="complete" if not missing else "incomplete-telemetry",
            measurement_start=start,
            measurement_end=end,
            missing_metrics=missing,
        )
        manifest["locust_final"] = http(locust + "/stats/requests")
        try:
            annotation(grafana, run_id, start, end)
        except (URLError, ValueError) as e:
            manifest["annotation_error"] = str(e)
    except BaseException as e:
        manifest.update(status="interrupted", error=str(e))
        raise
    finally:
        try:
            http(locust + "/stop", method="GET")
        except (URLError, ValueError):
            pass
        compose(["stop", "locust-worker", "locust-master"], env, args.sudo)
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Results: {output}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sudo", action="store_true", help="Run Docker commands through sudo")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("up")
    sub.add_parser("seed")
    sub.add_parser("down")
    run = sub.add_parser("run")
    run.add_argument("--replicas", default="1,2,4")
    run.add_argument("--users", type=int, default=100)
    run.add_argument("--workers", type=int, default=2)
    run.add_argument("--spawn-rate", type=float, default=10)
    run.add_argument("--warmup", type=int, default=30)
    run.add_argument("--seconds", type=int, default=120)
    run.add_argument(
        "--workload", choices=["balanced", "read-heavy", "hotspot"], default="balanced"
    )
    args = parser.parse_args()
    env = {
        **os.environ,
        "LOCAL_UID": str(ROOT.stat().st_uid),
        "LOCAL_GID": str(ROOT.stat().st_gid),
    }
    if args.command == "up":
        compose(["build"], env, args.sudo)
        compose(
            [
                "up",
                "-d",
                "api-gateway",
                "otel-collector",
                "prometheus",
                "grafana",
                "tempo",
                "cadvisor",
                "merchants-metrics",
                "catalog-metrics",
                "orders-metrics",
            ],
            env,
            args.sudo,
        )
    elif args.command == "seed":
        compose(["run", "--rm", "fixture-generate"], env, args.sudo)
        compose(["run", "--rm", "fixture-seed"], env, args.sudo)
    elif args.command == "down":
        compose(["down"], env, args.sudo)
    else:
        if not re.fullmatch(r"[1-9][0-9]*(,[1-9][0-9]*)*", args.replicas):
            parser.error("Use comma-separated positive replica counts")
        if min(args.users, args.workers, args.spawn_rate, args.seconds) < 1 or args.warmup < 0:
            parser.error("Counts/duration must be positive; warmup cannot be negative")
        if args.seconds < 30:
            parser.error("Use at least 30 measured seconds for 5s metric scrapes")
        if not (ROOT / "data/accounts.sqlite").exists():
            parser.error("Run the seed command first")
        for replicas in map(int, args.replicas.split(",")):
            experiment(args, replicas, env)


if __name__ == "__main__":
    main()

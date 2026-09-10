import json
import os
import random
from collections import Counter
from pathlib import Path
from uuid import uuid4

import gevent
from locust import FastHttpUser, between, events, task
from locust.runners import MasterRunner, WorkerRunner
from prometheus_client import CollectorRegistry, start_http_server

from accounts import Accounts
from metrics import LocustCollector

DOCUMENTS = json.loads(Path(__file__).with_name("graphql.json").read_text())


@events.init.add_listener
def initialize(environment, **kwargs):
    environment.load_reports = {}
    environment.order_outcomes = Counter()
    environment.accounts = None
    if not isinstance(environment.runner, MasterRunner):
        index = (
            environment.runner.worker_index if isinstance(environment.runner, WorkerRunner) else 0
        )
        workers = int(os.environ.get("LOAD_WORKERS", "1"))
        environment.accounts = Accounts(
            os.environ.get("ACCOUNTS_FILE", "/data/accounts.sqlite"), index, workers
        )
    if not isinstance(environment.runner, WorkerRunner):
        registry = CollectorRegistry()
        registry.register(LocustCollector(environment))
        environment.metrics_server = start_http_server(
            int(os.environ.get("LOCUST_METRICS_PORT", "9646")), registry=registry
        )


@events.report_to_master.add_listener
def report(client_id, data, **kwargs):
    env = ENV
    data["base_grid"] = {
        "visited": len(env.accounts.visited),
        "outcomes": dict(env.order_outcomes),
    }


@events.worker_report.add_listener
def receive(client_id, data, **kwargs):
    ENV.load_reports[client_id] = data.get("base_grid", {})


@events.init.add_listener
def remember(environment, **kwargs):
    global ENV
    ENV = environment
    if not isinstance(environment.runner, (MasterRunner, WorkerRunner)):

        def update():
            while True:
                environment.load_reports["local"] = {
                    "visited": len(environment.accounts.visited),
                    "outcomes": dict(environment.order_outcomes),
                }
                gevent.sleep(1)

        environment.local_reporter = gevent.spawn(update)


class KenyaMerchant(FastHttpUser):
    wait_time = between(
        float(os.environ.get("THINK_MIN", "1")), float(os.environ.get("THINK_MAX", "3"))
    )
    connection_timeout = 5
    network_timeout = 30
    max_retries = 0

    def on_start(self):
        self.pending = None
        self.actions = 0
        self.products = []
        self.choose_merchant()

    def choose_merchant(self):
        self.merchant = self.environment.accounts.next()
        self.auth = {"Authorization": "Bearer " + self.merchant["token"]}

    def call(self, operation, variables=None, headers=None, expected=None):
        with self.client.request(
            "POST",
            "/graphql",
            name=operation,
            json={"query": DOCUMENTS[operation], "variables": variables or {}},
            headers=headers or self.auth,
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201, 202):
                response.failure(f"HTTP {response.status_code}")
                return None
            try:
                result = response.json()
                if result.get("errors"):
                    response.failure(
                        "GraphQL " + result["errors"][0].get("extensions", {}).get("code", "ERROR")
                    )
                    return None
                data = result["data"][operation]
            except (ValueError, json.JSONDecodeError):
                response.failure("Invalid JSON")
                return None
            if expected and not expected(data):
                response.failure("Unexpected API outcome")
                return data
            return data

    @task
    def journey(self):
        if self.pending:
            self.finish_order()
            return
        self.actions += 1
        if self.actions % 5 == 0:
            self.choose_merchant()
        mode = os.environ.get("WORKLOAD", "balanced")
        weights = [85, 5, 5, 5] if mode == "read-heavy" else [50, 15, 10, 25]
        choice = random.choices(["browse", "profile", "history", "checkout"], weights=weights)[0]
        if choice == "browse":
            self.browse()
        elif choice == "profile":
            self.call("me")
        elif choice == "history":
            self.call("orders")
        else:
            self.checkout()

    def browse(self):
        data = self.call("products")
        if isinstance(data, list):
            self.products = [p for p in data if p["stock"] > 0]

    def checkout(self):
        if not self.products:
            self.browse()
        if not self.products:
            return
        candidates = self.products
        if os.environ.get("WORKLOAD") == "hotspot" and random.random() < 0.8:
            candidates = [p for p in candidates if p["id"] == "rice"] or candidates
        product = random.choice(candidates)
        items = [{"id": product["id"], "quantity": random.randint(1, 3)}]
        quote = self.call("quote", {"input": {"items": items}})
        if not isinstance(quote, dict) or "total" not in quote:
            self.products = []
            return
        self.pending = {
            "key": str(uuid4()),
            "body": {
                "items": items,
                "expectedTotal": quote["total"],
                "method": random.choice(["mobile", "card"]),
                "outcome": "declined"
                if random.random() < float(os.environ.get("DECLINE_RATE", ".02"))
                else "success",
            },
        }
        self.finish_order()

    def finish_order(self):
        pending = self.pending
        if "id" in pending:
            order = self.call(
                "order",
                {"id": pending["id"]},
                expected=lambda d: d.get("status") != "rejected",
            )
        else:
            order = self.call(
                "placeOrder",
                {"input": pending["body"], "idempotencyKey": pending["key"]},
                expected=lambda d: d.get("status") in ("pending", "confirmed", "declined"),
            )
        if not isinstance(order, dict) or "status" not in order:
            return
        if order["status"] == "pending":
            if "id" not in pending:
                self.environment.order_outcomes["pending"] += 1
            pending["id"] = order["id"]
            return
        self.environment.order_outcomes[order["status"]] += 1
        self.pending = None
        if order["status"] == "rejected":
            self.products = []


class RegistrationMerchant(KenyaMerchant):
    """Select explicitly to benchmark signup writes; not used in steady-state experiments."""

    @task
    def journey(self):
        self.choose_merchant()
        self.call(
            "createMerchant",
            {"input": self.merchant["profile"]},
            headers={"Content-Type": "application/json"},
        )


# Override the inherited task list so registration mode measures only signup.
RegistrationMerchant.tasks = [RegistrationMerchant.journey]

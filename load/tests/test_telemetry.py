import asyncio
from types import SimpleNamespace

from common.telemetry import RequestMetrics


class Instrument:
    def __init__(self):
        self.values = []

    def add(self, value, labels):
        self.values.append((value, labels))

    def record(self, value, labels):
        self.values.append((value, labels))


def test_metrics_normalize_route_ids_and_record_failures():
    requests = Instrument()
    duration = Instrument()

    async def app(scope, receive, send):
        scope["route"] = SimpleNamespace(path="/graphql")
        scope["graphql.operation"] = "placeOrder"
        scope["graphql.outcome"] = "error"
        await send({"type": "http.response.start", "status": 200})

    scope = {"type": "http", "path": "/graphql", "method": "POST"}

    async def send(message):
        pass

    asyncio.run(RequestMetrics(app, requests, duration)(scope, None, send))
    assert requests.values == [
        (
            1,
            {
                "route": "/graphql",
                "method": "POST",
                "status": "200",
                "operation": "placeOrder",
                "outcome": "error",
            },
        )
    ]
    assert duration.values[0][0] >= 0

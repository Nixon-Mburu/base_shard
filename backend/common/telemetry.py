"""Opt-in OTLP traces and low-cardinality metrics for every service replica."""

import atexit
import os
import socket
import time

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased


class RequestMetrics:
    def __init__(self, app, requests, duration):
        self.app = app
        self.requests = requests
        self.duration = duration

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") == "/health":
            return await self.app(scope, receive, send)
        start = time.perf_counter()
        status = 500

        async def observed(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, observed)
        finally:
            # Never use raw URLs: UUIDs and query strings must not create series.
            route = getattr(scope.get("route"), "path", "unmatched")
            attributes = {"route": route, "method": scope["method"], "status": str(status)}
            attributes["operation"] = scope.get("graphql.operation", "none")
            attributes["outcome"] = scope.get(
                "graphql.outcome", "error" if status >= 400 else "success"
            )
            self.requests.add(1, attributes)
            self.duration.record(time.perf_counter() - start, attributes)


def configure(app, service):
    if os.environ.get("OTEL_ENABLED", "false").lower() != "true":
        return
    resource = Resource.create(
        {
            "service.name": service,
            "service.instance.id": os.environ.get("SERVICE_INSTANCE_ID", socket.gethostname()),
            "deployment.environment.name": "load",
            "benchmark.run_id": os.environ.get("RUN_ID", "interactive"),
        }
    )
    tracer = TracerProvider(
        resource=resource,
        sampler=ParentBased(TraceIdRatioBased(float(os.environ.get("TRACE_SAMPLE_RATIO", ".01")))),
    )
    tracer.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer)
    reader = PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=5000)
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[reader],
        views=[
            View(
                instrument_name="base_api_duration",
                aggregation=ExplicitBucketHistogramAggregation(
                    [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 40]
                ),
            )
        ],
    )
    metrics.set_meter_provider(meter_provider)
    meter = meter_provider.get_meter("base-grid")
    count = meter.create_counter("base_api_requests", description="Completed HTTP requests")
    duration = meter.create_histogram(
        "base_api_duration", unit="s", description="Server request duration"
    )
    meter.create_observable_gauge(
        "base_api_heartbeat",
        callbacks=[lambda options: [metrics.Observation(time.time())]],
        description="Replica heartbeat epoch seconds",
    )
    # SQL bind parameters, bearer tokens and merchant profiles are not captured.
    HTTPXClientInstrumentor().instrument()
    PsycopgInstrumentor().instrument()
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
    app.add_middleware(RequestMetrics, requests=count, duration=duration)
    atexit.register(tracer.shutdown)
    atexit.register(meter_provider.shutdown)

import os

from fastapi import FastAPI

from common.graphql_api import mount
from common.http import graphql_request
from common.telemetry import configure

app = FastAPI(title="Base Grid GraphQL Gateway")
configure(app, "graphql-gateway")


@app.get("/health")
def health():
    return {"status": "ok", "service": "graphql-gateway"}


def delegate(service, operation):
    def resolve(_, info, **variables):
        return graphql_request(
            os.environ[service + "_URL"] + "/graphql",
            operation,
            variables,
            {"Authorization": info.context.headers.get("authorization", "")},
        )

    return resolve


mount(
    app,
    {
        name: delegate(service, name)
        for name, service in {
            "me": "MERCHANTS",
            "products": "CATALOG",
            "quote": "CATALOG",
            "orders": "ORDERS",
            "order": "ORDERS",
        }.items()
    },
    {
        name: delegate(service, name)
        for name, service in {
            "createMerchant": "MERCHANTS",
            "updateMerchant": "MERCHANTS",
            "placeOrder": "ORDERS",
        }.items()
    },
)

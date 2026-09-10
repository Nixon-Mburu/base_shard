import logging
import os
import secrets

import httpx
import psycopg
from fastapi import Header, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("base_grid")


def internal_access(x_service_key: str = Header(default="")):
    expected = os.environ["SERVICE_KEY"]
    if not x_service_key or not secrets.compare_digest(x_service_key, expected):
        raise HTTPException(403, "Internal service access required")


def request(method, url, **kwargs):
    try:
        with httpx.Client(timeout=8, trust_env=False) as client:
            response = client.request(method, url, **kwargs)
    except httpx.RequestError as exc:
        raise HTTPException(
            503, "A required service is temporarily unavailable. Retry shortly."
        ) from exc
    if response.is_error:
        try:
            detail = response.json().get("detail", "Service request failed")
        except ValueError:
            detail = "Service request failed"
        raise HTTPException(response.status_code if response.status_code < 500 else 503, detail)
    return response.json()


def merchant_session(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Set up your business to continue")
    return graphql_request(
        os.environ["MERCHANTS_URL"] + "/graphql", "me", {}, {"Authorization": authorization}
    )


def graphql_request(url, operation, variables, headers=None):
    from common.graphql_documents import DOCUMENTS

    result = request(
        "POST",
        url,
        json={"query": DOCUMENTS[operation], "variables": variables},
        headers=headers or {},
    )
    if result.get("errors"):
        error = result["errors"][0]
        raise HTTPException(error.get("extensions", {}).get("status", 503), error["message"])
    return result["data"][operation]


def add_database_errors(app):
    @app.exception_handler(psycopg.Error)
    async def database_error(_request, exc):
        logger.error("Database request failed: %s", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"detail": "Database temporarily unavailable. Please retry."},
        )

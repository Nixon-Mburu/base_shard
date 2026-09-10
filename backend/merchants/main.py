import hashlib
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from psycopg.types.json import Jsonb

from common.db import connect, migrate
from common.graphql_api import mount
from common.http import add_database_errors
from common.models import Merchant
from common.telemetry import configure


@asynccontextmanager
async def lifespan(_app):
    migrate(Path(__file__).parent / "migrations")
    yield


app = FastAPI(
    title="Base Grid Merchants",
    lifespan=lifespan,
    docs_url="/api/merchants/docs",
    openapi_url="/api/merchants/openapi.json",
)
add_database_errors(app)
configure(app, "merchants")


def current(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Set up your business to continue")
    digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
    with connect() as db:
        row = db.execute(
            "SELECT id, profile FROM merchants WHERE token_hash=%s", (digest,)
        ).fetchone()
    if not row:
        raise HTTPException(401, "Your business session is invalid. Set up your business again.")
    return {**row["profile"], "id": str(row["id"])}


@app.get("/health")
def health():
    with connect() as db:
        db.execute("SELECT 1")
    return {"status": "ok", "service": "merchants"}


def create(profile: Merchant):
    token = secrets.token_urlsafe(48)
    merchant_id = uuid4()
    with connect() as db:
        db.execute(
            "INSERT INTO merchants(id, profile, token_hash) VALUES (%s,%s,%s)",
            (
                merchant_id,
                Jsonb(profile.model_dump()),
                hashlib.sha256(token.encode()).hexdigest(),
            ),
        )
    return {
        "merchant": {**profile.model_dump(), "id": str(merchant_id)},
        "token": token,
    }


def me(merchant=Depends(current)):
    return merchant


def update(profile: Merchant, merchant=Depends(current)):
    with connect() as db:
        db.execute(
            "UPDATE merchants SET profile=%s, updated_at=now() WHERE id=%s",
            (Jsonb(profile.model_dump()), merchant["id"]),
        )
    return {**profile.model_dump(), "id": merchant["id"]}


mount(
    app,
    {"me": lambda _, info: current(info.context.headers.get("authorization", ""))},
    {
        "createMerchant": lambda _, info, input: create(Merchant(**input)),
        "updateMerchant": lambda _, info, input: update(
            Merchant(**input), current(info.context.headers.get("authorization", ""))
        ),
    },
)

"""Load fixture rows directly, outside the measured HTTP workload. Never deletes data."""

import argparse
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import psycopg
from psycopg.types.json import Jsonb


def seed(source, accounts, stock):
    if os.environ.get("LOAD_FIXTURE_DATABASES") != "true":
        raise SystemExit("Use the fixture-seed service in the isolated load Compose project.")
    secret_path = source.parent / "seed-secret"
    if not secret_path.exists():
        with secret_path.open("x") as f:
            f.write(secrets.token_hex(32))
        secret_path.chmod(0o600)
    secret = secret_path.read_bytes()
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    target = accounts.with_suffix(".sqlite.tmp")
    target.unlink(missing_ok=True)
    local = sqlite3.connect(target)
    local.execute(
        "CREATE TABLE accounts (idx INTEGER PRIMARY KEY, merchant_id TEXT NOT NULL, token TEXT NOT NULL, county TEXT NOT NULL, profile TEXT NOT NULL)"
    )
    local.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    count = 0
    with psycopg.connect(os.environ["MERCHANTS_DATABASE_URL"]) as db:
        db.execute(
            "CREATE TEMP TABLE fixture_merchants (LIKE merchants INCLUDING DEFAULTS) ON COMMIT DROP"
        )
        with (
            db.cursor().copy("COPY fixture_merchants(id,profile,token_hash) FROM STDIN") as copy,
            source.open() as rows,
        ):
            for line in rows:
                row = json.loads(line)
                idx = row["index"]
                if idx != count:
                    raise ValueError("Population indices must be contiguous from zero")
                token = hmac.new(
                    secret, f"{source_hash}:{idx}".encode(), hashlib.sha256
                ).hexdigest()
                mid = str(uuid5(NAMESPACE_URL, "base-grid-load:" + token))
                copy.write_row(
                    (
                        mid,
                        Jsonb(row["profile"]),
                        hashlib.sha256(token.encode()).hexdigest(),
                    )
                )
                local.execute(
                    "INSERT INTO accounts VALUES (?,?,?,?,?)",
                    (idx, mid, token, row["county"], json.dumps(row["profile"])),
                )
                count += 1
        db.execute(
            "INSERT INTO merchants(id,profile,token_hash) SELECT id,profile,token_hash FROM fixture_merchants ON CONFLICT DO NOTHING"
        )
    with psycopg.connect(os.environ["CATALOG_DATABASE_URL"]) as db:
        # Raise the floor only; no destructive reset, and never run while measuring.
        db.execute("UPDATE products SET stock=GREATEST(stock,%s)", (stock,))
    local.executemany(
        "INSERT INTO metadata VALUES (?,?)",
        [("count", str(count)), ("population_sha256", source_hash)],
    )
    local.commit()
    local.close()
    target.chmod(0o600)
    target.replace(accounts)
    print(
        json.dumps(
            {
                "merchants": count,
                "accounts_file": str(accounts),
                "minimum_stock": stock,
                "population_sha256": source_hash,
            }
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, default=Path("/data/merchants.jsonl"))
    p.add_argument("--accounts", type=Path, default=Path("/data/accounts.sqlite"))
    p.add_argument("--stock", type=int, default=10000000)
    a = p.parse_args()
    if a.stock < 1:
        raise SystemExit("Stock must be positive")
    seed(a.source, a.accounts, a.stock)

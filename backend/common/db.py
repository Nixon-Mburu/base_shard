import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, connect_timeout=5)


def migrate(directory):
    # Each service uses its own database and migration history.
    with connect() as db:
        db.execute("SELECT pg_advisory_xact_lock(872431)")
        db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        for path in sorted(Path(directory).glob("*.sql")):
            if not db.execute(
                "SELECT 1 FROM schema_migrations WHERE name=%s", (path.name,)
            ).fetchone():
                db.execute(path.read_text())
                db.execute("INSERT INTO schema_migrations(name) VALUES (%s)", (path.name,))

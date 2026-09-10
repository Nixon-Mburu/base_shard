import json
import sqlite3
from pathlib import Path


class Accounts:
    def __init__(self, path, worker_index=0, workers=1):
        self.db = sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True)
        self.count = int(
            self.db.execute("SELECT value FROM metadata WHERE key='count'").fetchone()[0]
        )
        if not 0 <= worker_index < workers or workers > self.count:
            raise ValueError(
                "Invalid worker partition; restart the run with the correct worker count"
            )
        self.worker_index = worker_index
        self.workers = workers
        self.cursor = worker_index
        self.visited = set()

    def next(self):
        idx = self.cursor
        self.cursor += self.workers
        if self.cursor >= self.count:
            self.cursor = self.worker_index
        row = self.db.execute(
            "SELECT merchant_id,token,county,profile FROM accounts WHERE idx=?", (idx,)
        ).fetchone()
        self.visited.add(idx)
        return {
            "id": row[0],
            "token": row[1],
            "county": row[2],
            "profile": json.loads(row[3]),
        }

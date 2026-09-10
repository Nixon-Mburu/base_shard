import json
import sqlite3
from collections import Counter
from pathlib import Path

from common.models import Merchant

from accounts import Accounts
from population import generate


def test_population_is_reproducible_and_covers_kenya():
    rows = list(generate(100000))
    assert len(rows) == 100000
    assert len({r["county"] for r in rows}) == 47
    assert len({r["profile"]["businessName"] for r in rows}) == 100000
    assert rows[:100] == list(generate(100))
    for row in rows[::100]:
        Merchant.model_validate(row["profile"])
    assert all(r["profile"]["phone"].startswith("000") for r in rows)


def test_hotspot_is_a_declared_nairobi_skew():
    counts = Counter(r["county"] for r in generate(10000, distribution="hotspot"))
    assert 0.55 < counts["Nairobi"] / 10000 < 0.65
    assert len(counts) == 47


def test_distributed_account_partitions_are_disjoint(tmp_path):
    path = tmp_path / "accounts.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE metadata(key TEXT,value TEXT)")
        db.execute("INSERT INTO metadata VALUES ('count','101')")
        db.execute(
            "CREATE TABLE accounts(idx INTEGER PRIMARY KEY,merchant_id TEXT,token TEXT,county TEXT,profile TEXT)"
        )
        db.executemany(
            "INSERT INTO accounts VALUES (?,?,?,?,?)",
            [(i, str(i), "fake", "Nairobi", "{}") for i in range(101)],
        )
    workers = [Accounts(path, i, 4) for i in range(4)]
    groups = [{w.next()["id"] for _ in range(30)} for w in workers]
    assert len(set.union(*groups)) == 101
    assert sum(map(len, groups)) == 101


def test_dashboard_has_bounded_queries_and_cpu_is_container_based():
    dashboard = json.loads(
        (Path(__file__).parents[1] / "observability/grafana/dashboards/base-grid.json").read_text()
    )
    ids = [p["id"] for p in dashboard["panels"]]
    assert len(ids) == len(set(ids))
    cpu = next(p for p in dashboard["panels"] if p.get("title", "").startswith("Database CPU"))
    assert "container_cpu_usage_seconds_total" in cpu["targets"][0]["expr"]
    assert "merchant_id" not in json.dumps(dashboard)

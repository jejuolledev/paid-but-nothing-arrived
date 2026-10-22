"""One SQL door for the agent.

The agent never touches a payment API, a database driver or a log file directly.
It asks a single SQL endpoint. In production that endpoint is Zetaris, which federates
the four sources without moving the data. For offline development and tests the same
queries run against the synthetic CSVs through DuckDB with identical table names.

  ZETARIS_SQL_URL / ZETARIS_API_KEY   -> ZetarisBackend (REST SQL)
  otherwise                           -> DuckDBBackend (local CSV)
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any

TABLES = ["payments", "orders", "grants", "server_logs", "mail_events"]
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "out"


class DuckDBBackend:
    name = "duckdb-local"

    def __init__(self, data_dir: Path = DATA_DIR):
        import duckdb  # local import keeps the Zetaris path dependency-free
        self.con = duckdb.connect(database=":memory:")
        for t in TABLES:
            p = data_dir / f"{t}.csv"
            if not p.exists():
                raise FileNotFoundError(f"{p} missing — run `python data/gen_synthetic.py` first")
            self.con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_csv_auto('{p}', header=true, all_varchar=true)")

    def query(self, sql: str) -> list[dict[str, Any]]:
        cur = self.con.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


class ZetarisBackend:
    """Minimal REST client. The exact path/payload is confirmed against the Zetaris
    OpenAPI spec of the supplied instance (see docs/HANDOVER.md, step Z-1)."""
    name = "zetaris"

    def __init__(self, url: str, api_key: str, schema: str = ""):
        import httpx
        self.url, self.schema = url.rstrip("/"), schema
        self.http = httpx.Client(timeout=60, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})

    def query(self, sql: str) -> list[dict[str, Any]]:
        if self.schema:
            for t in TABLES:
                sql = sql.replace(f" {t} ", f" {self.schema}.{t} ").replace(f" {t}\n", f" {self.schema}.{t}\n")
        r = self.http.post(f"{self.url}/sql", json={"sql": sql})
        r.raise_for_status()
        body = r.json()
        rows = body.get("rows") or body.get("data") or body
        cols = body.get("columns")
        if cols and rows and isinstance(rows[0], list):
            return [dict(zip(cols, row)) for row in rows]
        return rows


def get_backend():
    url, key = os.getenv("ZETARIS_SQL_URL"), os.getenv("ZETARIS_API_KEY")
    if url and key:
        return ZetarisBackend(url, key, os.getenv("ZETARIS_SCHEMA", ""))
    return DuckDBBackend()

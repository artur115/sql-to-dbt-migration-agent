"""Read the customer's legacy jobs, order them by dependency and run them."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from graphlib import TopologicalSorter
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
JOBS_DIR = ROOT / "customer" / "legacy_jobs"
DB_PATH = ROOT / "data" / "warehouse.duckdb"

LEGACY_SCHEMA = "legacy_reporting"
CANDIDATE_SCHEMA = "candidate"

_REF = re.compile(r"warehouse\.legacy_reporting\.(\w+)", re.I)
_HEADER = re.compile(r"^--\s*(\w+):\s*(.+)$", re.M)
# Things that make output depend on when or how often a job runs.
_RUNTIME_DEPENDENT = re.compile(
    r"\b(random\s*\(|uuid\s*\(|gen_random_uuid|current_date|current_timestamp|now\s*\(|today\s*\()",
    re.I,
)


@dataclass
class LegacyJob:
    name: str
    sql: str
    owner: str
    complexity: str
    description: str
    depends_on: set[str] = field(default_factory=set)

    @property
    def runtime_dependent(self) -> list[str]:
        body = "\n".join(l for l in self.sql.splitlines() if not l.lstrip().startswith("--"))
        return sorted({m.group(1).lower().rstrip("( ") for m in _RUNTIME_DEPENDENT.finditer(body)})


def load_jobs(jobs_dir: Path = JOBS_DIR) -> dict[str, LegacyJob]:
    jobs: dict[str, LegacyJob] = {}
    for path in sorted(jobs_dir.glob("*.sql")):
        sql = path.read_text()
        header = {k.lower(): v.strip() for k, v in _HEADER.findall(sql)}
        description = next(
            (l[2:].strip() for l in sql.splitlines()[3:4] if l.startswith("--")), ""
        )
        deps = {m.lower() for m in _REF.findall(sql)} - {path.stem}
        jobs[path.stem] = LegacyJob(
            name=path.stem,
            sql=sql,
            owner=header.get("owner", "unknown"),
            complexity=header.get("complexity", "unknown"),
            description=description,
            depends_on=deps,
        )
    return jobs


def run_order(jobs: dict[str, LegacyJob]) -> list[str]:
    graph = {name: job.depends_on & jobs.keys() for name, job in jobs.items()}
    return list(TopologicalSorter(graph).static_order())


def connect(path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(path))
    for schema in (LEGACY_SCHEMA, CANDIDATE_SCHEMA):
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    return con


def run_legacy(con: duckdb.DuckDBPyConnection, job: LegacyJob) -> None:
    """Run a legacy script as-is. Temp tables are dropped afterwards so jobs stay isolated."""
    con.execute(job.sql)
    for (tmp,) in con.execute(
        "SELECT table_name FROM duckdb_tables() WHERE temporary"
    ).fetchall():
        con.execute(f'DROP TABLE IF EXISTS temp."{tmp}"')

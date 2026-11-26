"""Rule-based translator: the "no AI" baseline.

It handles the mechanical part of a migration and nothing else:
  CREATE TEMP TABLE x AS ...       -> CTE x
  warehouse.raw.<t>                -> {{ source('raw', '<t>') }}
  warehouse.legacy_reporting.<m>   -> {{ ref('<m>') }}
  final CREATE TABLE ... AS SELECT -> the model's SELECT

Anything that changes a table after it is created (UPDATE, DELETE, INSERT)
needs the logic folded into the SELECT. A rule engine cannot do that safely,
so it gives up and says why.
"""
from __future__ import annotations

import re

import sqlglot
from sqlglot import exp

from .legacy import LegacyJob


class Unsupported(Exception):
    pass


_PLACEHOLDER = re.compile(r"__(src|ref)__(\w+?)__(\w+)__")


def _swap_tables(node: exp.Expression) -> exp.Expression:
    def visit(n: exp.Expression) -> exp.Expression:
        if isinstance(n, exp.Table) and n.catalog.lower() == "warehouse":
            schema, name = n.db.lower(), n.name
            kind = "src" if schema == "raw" else "ref" if schema == "legacy_reporting" else None
            if kind:
                new = exp.Table(this=exp.to_identifier(f"__{kind}__{schema}__{name}__"))
                if n.args.get("alias"):
                    new.set("alias", n.args["alias"])
                return new
        return n

    return node.transform(visit)


def _jinja(sql: str) -> str:
    def repl(m: re.Match) -> str:
        kind, schema, name = m.groups()
        return f"{{{{ source('{schema}', '{name}') }}}}" if kind == "src" else f"{{{{ ref('{name}') }}}}"

    return _PLACEHOLDER.sub(repl, sql)


def translate(job: LegacyJob) -> str:
    statements = [s for s in sqlglot.parse(job.sql, read="duckdb") if s is not None]
    ctes: list[tuple[str, exp.Expression]] = []
    final: exp.Expression | None = None
    for stmt in statements:
        if isinstance(stmt, exp.Create) and stmt.kind == "TABLE":
            target = stmt.this.this if isinstance(stmt.this, exp.Schema) else stmt.this
            temporary = any(isinstance(p, exp.TemporaryProperty)
                            for p in (stmt.args.get("properties") or exp.Properties()).expressions)
            if temporary:
                ctes.append((target.name, _swap_tables(stmt.expression)))
                continue
            if final is not None:
                raise Unsupported("more than one output table")
            final = _swap_tables(stmt.expression)
            continue
        kind = type(stmt).__name__.upper()
        raise Unsupported(f"{kind} statement changes the table after it is created")
    if final is None:
        raise Unsupported("no output table")

    existing = final.args.get("with_")
    inner = list(existing.expressions) if existing else []
    if existing:
        final.set("with_", None)
    with_ = exp.With(expressions=[exp.CTE(this=e, alias=exp.TableAlias(this=exp.to_identifier(n)))
                                  for n, e in ctes] + inner)
    if with_.expressions:
        if not isinstance(final, exp.Select):  # e.g. a UNION at the top level
            final = exp.select("*").from_(final.subquery("u"))
        final.set("with_", with_)
    sql = final.sql(dialect="duckdb", pretty=True)
    return _jinja(sql) + "\n"

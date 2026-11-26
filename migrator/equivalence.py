"""Is the migrated table the same data as the legacy table?

Rows are compared as a multiset (EXCEPT ALL in both directions), so order does
not matter but duplicates do. Numbers are compared after rounding to 6
decimals, so DECIMAL vs DOUBLE is not a mismatch; a different value is.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import duckdb

NUMERIC = ("TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT", "UTINYINT", "USMALLINT",
           "UINTEGER", "UBIGINT", "FLOAT", "DOUBLE", "REAL", "DECIMAL")


@dataclass
class Comparison:
    match: bool
    legacy_rows: int
    new_rows: int
    missing_columns: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)
    type_changes: dict[str, str] = field(default_factory=dict)
    only_in_legacy: int = 0
    only_in_new: int = 0
    sample_only_in_legacy: list[dict] = field(default_factory=list)
    sample_only_in_new: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def feedback(self) -> str:
        """Plain-language diff, used as the retry prompt for the agent."""
        if self.match:
            return "Outputs match."
        lines = [f"Legacy table has {self.legacy_rows} rows; your model returned {self.new_rows}."]
        if self.missing_columns:
            lines.append(f"Columns missing from your model: {', '.join(self.missing_columns)}.")
        if self.extra_columns:
            lines.append(f"Columns your model has that legacy does not: {', '.join(self.extra_columns)}.")
        if self.only_in_legacy or self.only_in_new:
            lines.append(
                f"{self.only_in_legacy} legacy rows have no identical row in your output; "
                f"{self.only_in_new} of your rows have no identical legacy row."
            )
        for label, rows in (("legacy only", self.sample_only_in_legacy), ("yours only", self.sample_only_in_new)):
            for row in rows[:3]:
                lines.append(f"  sample {label}: {row}")
        return "\n".join(lines)


def _columns(con: duckdb.DuckDBPyConnection, relation: str) -> dict[str, str]:
    rows = con.execute(f"DESCRIBE SELECT * FROM {relation}").fetchall()
    return {name.lower(): dtype.upper() for name, dtype, *_ in rows}


def _normalised(col: str, dtype: str) -> str:
    if dtype.startswith(NUMERIC):
        return f'ROUND(CAST("{col}" AS DOUBLE), 6)::VARCHAR AS "{col}"'
    return f'CAST("{col}" AS VARCHAR) AS "{col}"'


def compare(con: duckdb.DuckDBPyConnection, legacy: str, new: str, sample: int = 3) -> Comparison:
    lcols, ncols = _columns(con, legacy), _columns(con, new)
    missing = [c for c in lcols if c not in ncols]
    extra = [c for c in ncols if c not in lcols]
    common = [c for c in lcols if c in ncols]
    type_changes = {c: f"{lcols[c]} -> {ncols[c]}" for c in common if lcols[c] != ncols[c]}

    legacy_rows = con.execute(f"SELECT COUNT(*) FROM {legacy}").fetchone()[0]
    new_rows = con.execute(f"SELECT COUNT(*) FROM {new}").fetchone()[0]

    lsel = ", ".join(_normalised(c, lcols[c]) for c in common)
    nsel = ", ".join(_normalised(c, ncols[c]) for c in common)
    l_minus_n = f"SELECT {lsel} FROM {legacy} EXCEPT ALL SELECT {nsel} FROM {new}"
    n_minus_l = f"SELECT {nsel} FROM {new} EXCEPT ALL SELECT {lsel} FROM {legacy}"
    only_l = con.execute(f"SELECT COUNT(*) FROM ({l_minus_n})").fetchone()[0] if common else legacy_rows
    only_n = con.execute(f"SELECT COUNT(*) FROM ({n_minus_l})").fetchone()[0] if common else new_rows

    def rows(q: str) -> list[dict]:
        if not common:
            return []
        cur = con.execute(f"SELECT * FROM ({q}) LIMIT {sample}")
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]

    match = not missing and not extra and only_l == 0 and only_n == 0
    return Comparison(
        match=match, legacy_rows=legacy_rows, new_rows=new_rows,
        missing_columns=missing, extra_columns=extra, type_changes=type_changes,
        only_in_legacy=only_l, only_in_new=only_n,
        sample_only_in_legacy=[] if match else rows(l_minus_n),
        sample_only_in_new=[] if match else rows(n_minus_l),
    )

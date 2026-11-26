"""LLM translator: legacy job -> dbt model, with the diff fed back on each retry."""
from __future__ import annotations

import json

from .legacy import LegacyJob
from .llm import LLM

SYSTEM = """You migrate a customer's legacy warehouse SQL jobs to dbt models running on DuckDB.

Rules for the model you write:
- Return ONE SELECT statement. CTEs are fine. No DDL, no DML, no semicolon.
- Replace warehouse.raw.<table> with {{ source('raw', '<table>') }}.
- Replace warehouse.legacy_reporting.<model> with {{ ref('<model>') }}.
- Temp tables become CTEs.
- Fold any UPDATE, DELETE or INSERT that runs after the CREATE into the SELECT
  (CASE expressions, anti-joins, UNION ALL), applied in the same order as the script.
- The output must be identical to what the legacy job leaves in its table: same
  column names in the same order, same rows, same values, same row count.
- Keep legacy quirks exactly (integer division, rounding, how NULLs and duplicates
  are handled, odd join conditions). Do not fix bugs. List any quirk you notice in
  quirks_found so the job owner can decide later.
- If an exact equivalent is impossible (output depends on randomness or the run
  time, or the logic is ambiguous), set can_migrate to false and explain in notes.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "can_migrate": {"type": "boolean"},
        "model_sql": {"type": "string"},
        "notes": {"type": "string"},
        "quirks_found": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["can_migrate", "model_sql", "notes", "quirks_found"],
    "additionalProperties": False,
}


def first_prompt(job: LegacyJob, catalog: dict[str, list[str]], refs: dict[str, list[str]]) -> str:
    src = "\n".join(f"- raw.{t}: {', '.join(c)}" for t, c in sorted(catalog.items()))
    ref = "\n".join(f"- {m}: {', '.join(c)}" for m, c in sorted(refs.items())) or "- (none yet)"
    return (f"Legacy job `{job.name}` (owner: {job.owner}).\n\n```sql\n{job.sql}\n```\n\n"
            f"Source tables and columns:\n{src}\n\n"
            f"Already-migrated models you may ref():\n{ref}\n")


class Conversation:
    """One job's attempts. Each retry sees the earlier answer and what went wrong."""

    def __init__(self, llm: LLM, job: LegacyJob, catalog, refs):
        self.llm, self.job = llm, job
        self.messages = [{"role": "user", "content": first_prompt(job, catalog, refs)}]

    def propose(self) -> dict:
        out = self.llm.complete_json(SYSTEM, self.messages, SCHEMA, tag=self.job.name)
        self.messages.append({"role": "assistant", "content": json.dumps(out)})
        return out

    def feedback(self, text: str) -> None:
        self.messages.append({"role": "user", "content":
                              f"{text}\n\nRevise the model so its output matches the legacy table exactly."})

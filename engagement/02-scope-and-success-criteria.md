# 02 · Scope and success criteria

> Simulated engagement (see 01-discovery.md).

## In scope
- Translate each legacy job into one dbt model (`source()` / `ref()`, CTEs instead of temp tables).
- Fold post-create `UPDATE` / `DELETE` / `INSERT` logic into the model's `SELECT`.
- A parallel run: the legacy job and the candidate model both run on the same warehouse,
  and the outputs are compared row by row.
- A scorecard per job: accepted, rejected for mismatch, or sent to a person, with the reason.

## Out of scope (written down so nobody is surprised)
- Fixing legacy bugs. Quirks are kept and listed in model `meta` for the owner to decide later.
- Performance tuning. That is a second phase, once the dbt models are the source of truth.
- Jobs whose output depends on run time or randomness. Those need an owner decision
  (a fixed as-of date or a seed) before they can be compared at all.

## Success criteria
| Criterion | How it is checked |
|---|---|
| Zero mismatches shipped | `scripts/verify_dbt.py` compares every built dbt model with its legacy table and fails CI on any difference |
| Every job has an outcome and a reason | `report/scorecard_*.md` |
| The AI adds value over a rule engine | Same 24 jobs through a rule-based translator (`--translator baseline`) and the agent (`--translator llm`) |
| Reproducible without an API key | Agent responses are recorded; CI replays them |

## Approach
1. Rule-based baseline first. It is cheap, deterministic and handles the mechanical jobs.
2. The agent on the same jobs, with up to three attempts. After a failed attempt it gets
   the diff: missing columns, row counts, sample rows only on one side.
3. Gate: accepted only on an exact match; anything else goes to the owner.

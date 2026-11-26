# 03 · Handoff

> Simulated engagement (see 01-discovery.md).

## What the customer gets
- `dbt_project/` with the accepted models and an owner and the kept quirks on each model (`_migrated.yml`).
- `report/scorecard_*.md`: one line per job with its outcome and reason.
- A CI workflow that rebuilds the warehouse, runs the models and fails on any mismatch.

## What needs an owner decision
Read the "needs_human" and "rejected_mismatch" rows in the scorecard. The typical asks:
- **qa_sample_orders** (data-platform): it samples with `random()`. Pick a seed, or keep it out of dbt.
- **open_orders_snapshot** (ops-analytics): it filters on `current_date`. Agree an as-of date
  variable so the job can be tested.
- Any listed legacy quirk: keep, or fix in a follow-up change with a visible diff.

## How to run it again
```bash
make demo
```

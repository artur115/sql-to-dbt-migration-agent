# 01 · Discovery notes

> **Simulated engagement.** Harbor & Pine Outfitters is a made-up company and all of its
> data is synthetic. This document shows how I would run the first week with a real customer.

## The ask, in the customer's words
"We have two dozen nightly SQL jobs that nobody wants to touch. We want them in dbt so we
get lineage, tests and code review, but finance will not accept a single number changing."

## What I found in the first two days
| Question | Answer |
|---|---|
| How many jobs? | 24 SQL scripts in `customer/legacy_jobs/`, owned by six teams |
| How do they run? | A scheduler runs each script; each one writes one table in `legacy_reporting` |
| Patterns | Temp-table chains, hard-coded `warehouse.raw.*` names, jobs reading other jobs' output |
| Risky patterns | `UPDATE` / `DELETE` / `INSERT` after the `CREATE` (5 jobs), `random()` and `current_date` (2 jobs) |
| Legacy quirks | Integer division in `repeat_purchase_rate`, a join that drops re-delivered orders in `return_rate_by_category` |
| Who signs off? | The owner in each script header; finance-analytics for anything with revenue |

## What "done" means to them
1. Every migrated table returns exactly the same rows as the legacy job: same columns,
   same values, same row count.
2. Nothing that differs ships. A person sees why, and decides.
3. Quirks are kept, not silently fixed, and are written down for the owner.

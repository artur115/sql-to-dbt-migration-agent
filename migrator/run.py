"""Migrate every legacy job, check it against a parallel run, and score the result.

    python -m migrator.run --translator baseline
    python -m migrator.run --translator llm --mode replay     # CI, no key
    python -m migrator.run --translator llm --mode record     # real run, needs ANTHROPIC_API_KEY

A job is only accepted when its dbt model, run in the candidate schema, returns
exactly the rows the legacy job leaves in legacy_reporting. Everything else is
rejected or sent to a person with the reason.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from . import baseline
from .agent import Conversation
from .equivalence import compare
from .legacy import (CANDIDATE_SCHEMA, LEGACY_SCHEMA, ROOT, connect, load_jobs, run_legacy,
                     run_order)
from .llm import LLM, MissingRecording, ModelRefused

MODELS_DIR = ROOT / "dbt_project" / "models" / "migrated"
REPORT_DIR = ROOT / "report"
_JINJA = re.compile(r"\{\{\s*(source|ref)\(\s*'(\w+)'\s*(?:,\s*'(\w+)'\s*)?\)\s*\}\}")


@dataclass
class Result:
    job: str
    owner: str
    complexity: str
    status: str            # accepted | rejected_mismatch | needs_human
    reason: str
    attempts: int = 0
    legacy_rows: int = 0
    quirks_found: list[str] = field(default_factory=list)
    model_sql: str = ""


def render(model_sql: str) -> str:
    """Resolve source()/ref() the way dbt would, for the candidate run."""
    def repl(m: re.Match) -> str:
        kind, a, b = m.groups()
        return f"warehouse.raw.{b}" if kind == "source" else f"warehouse.{CANDIDATE_SCHEMA}.{a}"

    sql = _JINJA.sub(repl, model_sql).strip().rstrip(";")
    if "{{" in sql or "{%" in sql:
        raise ValueError("model uses Jinja other than source() and ref()")
    return sql


def catalog(con) -> dict[str, list[str]]:
    rows = con.execute("""SELECT table_name, column_name FROM information_schema.columns
                          WHERE table_schema = 'raw' ORDER BY table_name, ordinal_position""").fetchall()
    out: dict[str, list[str]] = {}
    for t, c in rows:
        out.setdefault(t, []).append(c)
    return out


def columns_of(con, schema: str, table: str) -> list[str]:
    return [r[0] for r in con.execute(f"DESCRIBE {schema}.{table}").fetchall()]


def try_model(con, job_name: str, model_sql: str) -> tuple[bool, str, dict | None]:
    try:
        sql = render(model_sql)
        con.execute(f"CREATE OR REPLACE TABLE {CANDIDATE_SCHEMA}.{job_name} AS {sql}")
    except Exception as e:  # the model did not run
        return False, f"Your model failed to run: {type(e).__name__}: {str(e)[:600]}", None
    cmp = compare(con, f"{LEGACY_SCHEMA}.{job_name}", f"{CANDIDATE_SCHEMA}.{job_name}")
    return cmp.match, cmp.feedback(), cmp.to_dict()


def migrate(translator: str, mode: str, max_attempts: int) -> list[Result]:
    jobs = load_jobs()
    con = connect()
    con.execute(f"DROP SCHEMA IF EXISTS {CANDIDATE_SCHEMA} CASCADE; CREATE SCHEMA {CANDIDATE_SCHEMA}")
    cat = catalog(con)
    llm = LLM(mode, ROOT / "recordings") if translator == "llm" else None
    accepted: dict[str, list[str]] = {}
    results: list[Result] = []

    for name in run_order(jobs):
        job = jobs[name]
        run_legacy(con, job)
        legacy_rows = con.execute(f"SELECT COUNT(*) FROM {LEGACY_SCHEMA}.{name}").fetchone()[0]
        res = Result(name, job.owner, job.complexity, "needs_human", "", legacy_rows=legacy_rows)
        results.append(res)

        blocked = sorted(d for d in job.depends_on if d not in accepted)
        if blocked:
            res.reason = f"depends on a job that is not migrated yet: {', '.join(blocked)}"
            continue
        if job.runtime_dependent:
            res.reason = (f"output depends on when it runs ({', '.join(job.runtime_dependent)}); "
                          "agree a fixed as-of date or seed with the owner")
            continue

        if translator == "baseline":
            res.attempts = 1
            try:
                res.model_sql = baseline.translate(job)
            except baseline.Unsupported as e:
                res.reason = f"rule-based translator can't express it: {e}"
                continue
            ok, feedback, _ = try_model(con, name, res.model_sql)
            res.status, res.reason = ("accepted", "parallel run matches") if ok else ("rejected_mismatch", feedback)
        else:
            conv = Conversation(llm, job, cat, accepted)
            for attempt in range(1, max_attempts + 1):
                res.attempts = attempt
                try:
                    out = conv.propose()
                except MissingRecording:
                    res.reason = "no recorded response for this prompt (run with --mode record)"
                    break
                except ModelRefused as e:
                    res.reason = f"model declined: {e}"
                    break
                res.model_sql, res.quirks_found = out["model_sql"], out["quirks_found"]
                if not out["can_migrate"]:
                    res.reason = f"agent says it can't be migrated exactly: {out['notes']}"
                    break
                ok, feedback, _ = try_model(con, name, out["model_sql"])
                if ok:
                    res.status, res.reason = "accepted", f"parallel run matches (attempt {attempt})"
                    break
                res.status, res.reason = "rejected_mismatch", feedback
                if attempt < max_attempts:
                    conv.feedback(feedback)

        if res.status == "accepted":
            accepted[name] = columns_of(con, CANDIDATE_SCHEMA, name)
        else:
            con.execute(f"DROP TABLE IF EXISTS {CANDIDATE_SCHEMA}.{name}")
    con.close()
    if llm:
        results_usage = llm.usage
        (REPORT_DIR / f"usage_{translator}.json").write_text(json.dumps(
            {"model": llm.model, "effort": llm.effort, **asdict(results_usage),
             "cost_usd": results_usage.cost_usd(llm.model), "mode": mode}, indent=2) + "\n")
    return results


def write_models(results: list[Result]) -> None:
    if MODELS_DIR.exists():
        shutil.rmtree(MODELS_DIR)
    MODELS_DIR.mkdir(parents=True)
    models = []
    for r in results:
        if r.status != "accepted":
            continue
        (MODELS_DIR / f"{r.job}.sql").write_text(r.model_sql.rstrip().rstrip(";") + "\n")
        meta = {"owner": r.owner, "migrated_from": f"customer/legacy_jobs/{r.job}.sql"}
        if r.quirks_found:
            meta["legacy_quirks_kept"] = r.quirks_found
        models.append({"name": r.job, "meta": meta})
    (MODELS_DIR / "_migrated.yml").write_text(yaml.safe_dump({"version": 2, "models": models},
                                                             sort_keys=False))


def write_report(results: list[Result], translator: str) -> dict:
    REPORT_DIR.mkdir(exist_ok=True)
    counts = {s: sum(r.status == s for r in results) for s in ("accepted", "rejected_mismatch", "needs_human")}
    by_tier = {}
    for tier in ("simple", "medium", "hard"):
        rs = [r for r in results if r.complexity == tier]
        by_tier[tier] = {"jobs": len(rs), "accepted": sum(r.status == "accepted" for r in rs)}
    summary = {"translator": translator, "jobs": len(results), **counts, "by_complexity": by_tier}
    (REPORT_DIR / f"scorecard_{translator}.json").write_text(json.dumps(
        {"summary": summary, "jobs": [asdict(r) for r in results]}, indent=2, default=str) + "\n")

    lines = [f"# Migration scorecard: {translator} translator", "",
             f"{counts['accepted']} of {len(results)} jobs accepted, "
             f"{counts['rejected_mismatch']} rejected for mismatch, {counts['needs_human']} sent to a person.", "",
             "| Job | Owner | Complexity | Status | Attempts | Why |", "|---|---|---|---|---:|---|"]
    for r in sorted(results, key=lambda r: (["simple", "medium", "hard"].index(r.complexity), r.job)):
        why = r.reason.splitlines()[0].replace("|", "\\|")[:140]
        lines.append(f"| {r.job} | {r.owner} | {r.complexity} | {r.status} | {r.attempts} | {why} |")
    (REPORT_DIR / f"scorecard_{translator}.md").write_text("\n".join(lines) + "\n")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--translator", choices=["baseline", "llm"], default="baseline")
    ap.add_argument("--mode", choices=["replay", "record", "live"], default="replay")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--write-models", action="store_true",
                    help="write accepted models into dbt_project/models/migrated")
    args = ap.parse_args()
    t0 = time.time()
    results = migrate(args.translator, args.mode, args.max_attempts)
    summary = write_report(results, args.translator)
    if args.write_models:
        write_models(results)
    print(json.dumps(summary, indent=2))
    print(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()

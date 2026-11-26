import json

import duckdb
import pytest

from migrator import baseline
from migrator.agent import Conversation
from migrator.equivalence import compare
from migrator.legacy import LegacyJob, connect, run_legacy, run_order
from migrator.llm import LLM, MissingRecording
from migrator.run import render, try_model


@pytest.fixture
def con(tmp_path):
    # The file must be called warehouse.duckdb: legacy SQL says warehouse.raw.*
    c = connect(tmp_path / "warehouse.duckdb")
    c.execute("CREATE SCHEMA raw")
    c.execute("CREATE TABLE raw.orders AS SELECT * FROM (VALUES "
              "(1, 10, 'Shipped '), (2, 10, 'shipped'), (3, 11, 'CANCELLED'), (3, 11, 'cancelled')"
              ") t(order_id, customer_id, status)")
    yield c
    c.close()


def job(name, sql, **kw):
    return LegacyJob(name=name, sql=sql, owner="test", complexity="simple", description="", **kw)


# --- equivalence ---------------------------------------------------------

def test_identical_tables_match(con):
    con.execute("CREATE TABLE a AS SELECT * FROM raw.orders")
    con.execute("CREATE TABLE b AS SELECT * FROM raw.orders ORDER BY order_id DESC")
    assert compare(con, "a", "b").match


def test_changed_value_is_caught(con):
    con.execute("CREATE TABLE a AS SELECT * FROM raw.orders")
    con.execute("CREATE TABLE b AS SELECT order_id, customer_id, "
                "CASE WHEN order_id = 2 THEN 'x' ELSE status END AS status FROM raw.orders")
    c = compare(con, "a", "b")
    assert not c.match and c.only_in_legacy == 1 and c.only_in_new == 1


def test_lost_duplicate_is_caught(con):
    # Order 3 arrives twice; after normalising status the two rows are identical.
    con.execute("CREATE TABLE a AS SELECT order_id, LOWER(TRIM(status)) AS s FROM raw.orders")
    con.execute("CREATE TABLE b AS SELECT DISTINCT * FROM a")
    c = compare(con, "a", "b")
    assert not c.match and (c.legacy_rows, c.new_rows, c.only_in_legacy) == (4, 3, 1)


def test_decimal_vs_double_is_not_a_mismatch(con):
    con.execute("CREATE TABLE a AS SELECT 1.50::DECIMAL(10,2) AS amt")
    con.execute("CREATE TABLE b AS SELECT 1.5::DOUBLE AS amt")
    c = compare(con, "a", "b")
    assert c.match and "amt" in c.type_changes


def test_missing_column_is_caught_and_explained(con):
    con.execute("CREATE TABLE a AS SELECT * FROM raw.orders")
    con.execute("CREATE TABLE b AS SELECT order_id, customer_id FROM raw.orders")
    c = compare(con, "a", "b")
    assert not c.match and c.missing_columns == ["status"]
    assert "status" in c.feedback()


# --- baseline translator --------------------------------------------------

LEGACY = """-- job: clean
CREATE TEMP TABLE tmp AS SELECT * FROM warehouse.raw.orders WHERE customer_id = 10;
CREATE OR REPLACE TABLE warehouse.legacy_reporting.clean AS
SELECT t.order_id FROM tmp t JOIN warehouse.legacy_reporting.other o ON o.id = t.order_id;
"""


def test_baseline_turns_temp_tables_into_ctes_and_tables_into_jinja():
    sql = baseline.translate(job("clean", LEGACY))
    assert sql.lstrip().upper().startswith("WITH TMP AS")
    assert "{{ source('raw', 'orders') }}" in sql
    assert "{{ ref('other') }}" in sql
    assert "warehouse." not in sql


def test_baseline_refuses_dml():
    j = job("x", "CREATE OR REPLACE TABLE warehouse.legacy_reporting.x AS SELECT 1 AS a;\n"
                 "UPDATE warehouse.legacy_reporting.x SET a = 2;")
    with pytest.raises(baseline.Unsupported, match="UPDATE"):
        baseline.translate(j)


# --- rendering, legacy helpers -------------------------------------------

def test_render_resolves_source_and_ref():
    out = render("select * from {{ source('raw', 'orders') }} join {{ ref('m') }} using (id);")
    assert out == "select * from warehouse.raw.orders join warehouse.candidate.m using (id)"


def test_render_rejects_other_jinja():
    with pytest.raises(ValueError):
        render("select {{ var('x') }}")


def test_runtime_dependence_is_detected_but_not_in_comments():
    assert job("a", "-- uses random() in the old days\nSELECT 1").runtime_dependent == []
    assert job("b", "SELECT * FROM t WHERE d >= current_date").runtime_dependent == ["current_date"]


def test_run_order_puts_dependencies_first():
    jobs = {"b": job("b", "", depends_on={"a"}), "a": job("a", "")}
    assert run_order(jobs) == ["a", "b"]


def test_legacy_run_drops_its_temp_tables(con):
    run_legacy(con, job("clean", "CREATE TEMP TABLE tmp AS SELECT 1 AS x;\n"
                        "CREATE OR REPLACE TABLE warehouse.legacy_reporting.clean AS SELECT * FROM tmp;"))
    assert con.execute("SELECT COUNT(*) FROM duckdb_tables() WHERE temporary").fetchone()[0] == 0


# --- LLM record/replay and the retry loop ----------------------------------

SCHEMA = {"type": "object"}


def test_replay_without_recording_fails_loudly(tmp_path):
    with pytest.raises(MissingRecording):
        LLM("replay", tmp_path).complete_json("sys", [{"role": "user", "content": "hi"}], SCHEMA)


def test_record_then_replay_returns_the_same_answer(tmp_path, monkeypatch):
    answer = {"ok": True}
    monkeypatch.setattr(LLM, "_call", lambda self, s, m, sc: (answer, {"input_tokens": 5, "output_tokens": 2}))
    msgs = [{"role": "user", "content": "hi"}]
    assert LLM("record", tmp_path).complete_json("sys", msgs, SCHEMA) == answer
    monkeypatch.setattr(LLM, "_call", lambda *a: pytest.fail("replay must not call the API"))
    replay = LLM("replay", tmp_path)
    assert replay.complete_json("sys", msgs, SCHEMA) == answer
    assert replay.usage.input_tokens == 5
    # A different prompt is a different recording.
    with pytest.raises(MissingRecording):
        replay.complete_json("sys v2", msgs, SCHEMA)


def test_retry_loop_feeds_the_diff_back_and_accepts_a_fixed_model(con, tmp_path, monkeypatch):
    legacy = job("clean", "CREATE OR REPLACE TABLE warehouse.legacy_reporting.clean AS "
                          "SELECT order_id, LOWER(TRIM(status)) AS status FROM warehouse.raw.orders;")
    run_legacy(con, legacy)
    answers = iter([
        {"can_migrate": True, "notes": "", "quirks_found": [],
         "model_sql": "select distinct order_id, lower(trim(status)) as status from {{ source('raw', 'orders') }}"},
        {"can_migrate": True, "notes": "", "quirks_found": ["duplicate order 3 kept"],
         "model_sql": "select order_id, lower(trim(status)) as status from {{ source('raw', 'orders') }}"},
    ])
    seen = []

    def fake_call(self, system, messages, schema):
        seen.append(json.dumps(messages))
        return next(answers), {"input_tokens": 1, "output_tokens": 1}

    monkeypatch.setattr(LLM, "_call", fake_call)
    conv = Conversation(LLM("live", tmp_path), legacy, {"orders": ["order_id"]}, {})
    ok, feedback, _ = try_model(con, "clean", conv.propose()["model_sql"])
    assert not ok and "4 rows" in feedback          # DISTINCT lost a duplicate
    conv.feedback(feedback)
    ok, _, _ = try_model(con, "clean", conv.propose()["model_sql"])
    assert ok
    assert "4 rows" in seen[1]                      # the second attempt saw the diff

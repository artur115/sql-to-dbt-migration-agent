"""The shipping gate: after `dbt build`, every dbt model must equal its legacy table.

Exit code 1 if any shipped model differs. This is what "0 mismatches shipped" means.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from migrator.equivalence import compare  # noqa: E402
from migrator.legacy import connect  # noqa: E402

models = sorted(p.stem for p in (ROOT / "dbt_project" / "models" / "migrated").glob("*.sql"))
con = connect()
bad = []
for m in models:
    c = compare(con, f"legacy_reporting.{m}", f"migrated.{m}")
    if not c.match:
        bad.append({"model": m, **c.to_dict()})
print(json.dumps({"models_shipped": len(models), "mismatches_shipped": len(bad)}, indent=2))
for b in bad:
    print(f"MISMATCH {b['model']}: {b['only_in_legacy']} legacy-only rows, {b['only_in_new']} new-only rows")
sys.exit(1 if bad else 0)

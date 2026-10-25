"""Write docs/claims_register.csv: every claim the app can show, with its source. Judges will ask."""
import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import core
out = Path(__file__).resolve().parent.parent / "docs"; out.mkdir(exist_ok=True)
rows = []
for c in core.CONDITIONS:
    rows += [("Module 2", c["name"], f"Textbook: {t}", "; ".join(c["sources"]), c["verification_status"]) for t in c["textbook"]]
    rows += [("Module 2", c["name"], f"Female presentation: {t}", "; ".join(c["sources"]), c["verification_status"]) for t in c["female"]]
    rows += [("Module 2", c["name"], f"Often-skipped test: {t}", "; ".join(c["sources"]), c["verification_status"]) for t in c["skipped_tests"]]
for m in core.ALTERNATIVES["methods"]:
    rows += [("Module 4", m["method"], f"Typical-use failure %: {m['typical_use_failure_pct']}", "; ".join(m["sources"]), m["verification_status"]),
             ("Module 4", m["method"], f"Mood evidence: {m['mood_evidence']}", "; ".join(m["sources"]), m["verification_status"])]
for d in core.DRUGS:
    rows.append(("Module 1/3", d["generic_name"], f"Data origin: {d.get('data_origin')}", "; ".join(d["sources"]), "REPLACE demo_seed via pipeline" if d.get("data_origin") == "demo_seed" else "live"))
    if d.get("sex_specific_dosing_note"):
        rows.append(("Module 3", d["generic_name"], d["sex_specific_dosing_note"], "; ".join(d["sources"]), "needs_review"))
for c in core.CASCADES:
    rows.append(("Module 3", c["id"], c["description"], "; ".join(c["sources"]), "needs_review"))
with open(out / "claims_register.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["module", "subject", "claim", "source", "status"]); w.writerows(rows)
print(f"wrote {len(rows)} claims to {out/'claims_register.csv'}")

"""Pull live data for each drug and merge into data/drugs.json.
Usage:  python -m pipeline.run_pipeline --csv data/drug_list.csv     # recommended: ~75 drugs
        python -m pipeline.run_pipeline                             # refresh drugs already in drugs.json
        python -m pipeline.run_pipeline --drugs naproxen,fluoxetine # specific drugs
Safe to re-run: responses are cached in data/cache/ ; a failed source keeps old values; progress is saved after every drug."""
import argparse, csv, json, datetime, re
from pathlib import Path
from . import clinicaltrials, openfda, pubmed

F = Path(__file__).resolve().parent.parent / "data" / "drugs.json"

def label_terms(label_text, reactions):
    """Reaction names (from FAERS) that also appear as whole words in the label's adverse-reactions text."""
    t = (label_text or "").lower()
    return sorted({r["reaction"].lower() for r in reactions
                   if re.search(r"\b" + re.escape(r["reaction"].lower()) + r"\b", t)})

def save(db, by):
    db["drugs"] = list(by.values())
    db["_note"] = "Entries with data_origin=demo_seed are illustrative placeholders."
    F.write_text(json.dumps(db, indent=2))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drugs", help="comma-separated generic names")
    ap.add_argument("--csv", help="CSV with columns generic,class,aliases (aliases separated by ;)")
    a = ap.parse_args()
    db = json.loads(F.read_text()); by = {d["generic_name"]: d for d in db["drugs"]}
    names = [x.strip().lower() for x in a.drugs.split(",")] if a.drugs else None
    if a.csv:
        names = names or []
        for row in csv.DictReader(open(a.csv, encoding="utf-8")):
            g = row["generic"].strip().lower(); names.append(g)
            rec = by.setdefault(g, {"name": g, "generic_name": g, "drug_class": row["class"], "aliases": []})
            if rec.get("drug_class") in (None, "unknown"): rec["drug_class"] = row["class"]
            rec["aliases"] = sorted(set(rec.get("aliases", [])) | {x.strip().lower() for x in row["aliases"].split(";") if x.strip()})
    names = names or list(by)
    for n, g in enumerate(names, 1):
        print(f"== [{n}/{len(names)}] {g}")
        rec = by.setdefault(g, {"name": g, "generic_name": g, "drug_class": "unknown", "aliases": []})
        got = []
        for label, fn in (("clinicaltrials", clinicaltrials.fetch), ("openfda label", openfda.label), ("faers", openfda.faers), ("pubmed", pubmed.fetch)):
            try:
                out = fn(g)
            except Exception as e:
                print(f"  ! {label} failed: {e}"); out = {}
            if out:
                rec.update({k: v for k, v in out.items() if v is not None}); got.append(label)
            else:
                print(f"  - {label}: no data (kept previous values)")
        if got:
            q = g.replace(" ", "+")
            rec["data_origin"] = "live_pipeline" if len(got) == 4 else "partial_live(" + ",".join(got) + ")"
            rec["retrieved_on"] = datetime.date.today().isoformat()
            text = rec.pop("label_adverse_reactions_text", "")
            terms = label_terms(text, rec.get("adverse_events_by_sex", []))
            if terms: rec["label_adverse_terms"] = terms
            rec.setdefault("label_adverse_terms", [])
            rec["sources"] = [f"https://clinicaltrials.gov/search?intr={q}", f"https://api.fda.gov/drug/label.json?search=openfda.generic_name:%22{q}%22",
                              f"https://pubmed.ncbi.nlm.nih.gov/?term={q}+pregnancy"]
        print(f"  sources ok: {got}")
        save(db, by)
    print("Saved", F, "| drugs:", len(by))

if __name__ == "__main__":
    main()

"""Loads the JSON 'database' files and resolves drug names (brand/generic/typos)."""
import json, os, difflib
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))

def load(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))

def _load_all():
    global DRUGS, DRUG_INDEX, SYMPTOMS, SYMPTOM_BY_ID, CONDITIONS, CASCADES, ALTERNATIVES
    DRUGS = load("drugs.json")["drugs"]
    DRUG_INDEX = {}
    for d in DRUGS:
        for n in [d["name"], d["generic_name"], *d.get("aliases", [])]:
            DRUG_INDEX[n.lower().strip()] = d
    SYMPTOMS = load("symptoms.json")
    SYMPTOM_BY_ID = {s["id"]: s for s in SYMPTOMS}
    CONDITIONS = load("conditions.json")
    CASCADES = load("cascades.json")
    ALTERNATIVES = load("alternatives.json")

_load_all()

def find_drug(name: str):
    """Exact match on generic/brand/alias, then fuzzy match. Returns record or None."""
    key = (name or "").lower().strip()
    if key in DRUG_INDEX:
        return DRUG_INDEX[key]
    close = difflib.get_close_matches(key, DRUG_INDEX.keys(), n=1, cutoff=0.8)
    return DRUG_INDEX[close[0]] if close else None

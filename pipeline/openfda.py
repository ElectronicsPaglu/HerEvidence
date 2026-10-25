"""openFDA drug labels + FAERS (sex-split). In FAERS patientsex: 1 = male, 2 = female."""
import os, re
from .http import get_json

KEY = os.getenv("OPENFDA_API_KEY")
LABEL = "https://api.fda.gov/drug/label.json"
EVENT = "https://api.fda.gov/drug/event.json"
_k = lambda p: dict(p, **({"api_key": KEY} if KEY else {}))

HUMAN_RE = re.compile(r"human data|epidemiolog|pregnancy registr|human studies|observational|cohort|case reports|postmarketing", re.I)
DOSE_SEX_RE = re.compile(r"(wom[ae]n|females?)[^.]{0,100}(dose|dosage|clearance|blood levels?)|(dose|dosage|clearance)[^.]{0,100}(wom[ae]n|females?)", re.I)
join = lambda x: " ".join(x) if isinstance(x, list) else (x or "")

def label(generic):
    d = get_json(LABEL, _k({"search": f'openfda.generic_name:"{generic}"', "limit": 1}))
    if not d or not d.get("results"): return {}
    r = d["results"][0]
    preg = join(r.get("pregnancy")) or join(r.get("use_in_specific_populations"))
    lact = join(r.get("lactation")) or join(r.get("nursing_mothers"))
    dosing = join(r.get("dosage_and_administration")) + " " + join(r.get("use_in_specific_populations"))
    return {"label_has_human_pregnancy_data": bool(HUMAN_RE.search(preg)),
            "label_has_lactation_data": len(lact) > 50,
            "has_sex_specific_dosing_info": bool(DOSE_SEX_RE.search(dosing)),
            "label_adverse_reactions_text": join(r.get("adverse_reactions"))[:20000].lower()}

def _count(generic, field, sex=None):
    s = f'patient.drug.openfda.generic_name:"{generic}"' + (f" AND patient.patientsex:{sex}" if sex else "")
    for limit in (1000, 100):                      # fall back to a smaller request if the big one is refused
        d = get_json(EVENT, _k({"search": s, "count": field, "limit": limit}))
        if d: return {x["term"]: x["count"] for x in d.get("results", [])}
    return {}

def faers(generic):
    sexes = _count(generic, "patient.patientsex")
    f, m = sexes.get(2, 0), sexes.get(1, 0)
    if f + m == 0: return {}
    fr = _count(generic, "patient.reaction.reactionmeddrapt.exact", 2)
    mr = _count(generic, "patient.reaction.reactionmeddrapt.exact", 1)
    rows = [{"reaction": r, "female_count": fr.get(r, 0), "male_count": mr.get(r, 0),
             "female_share": round(fr.get(r, 0) / (fr.get(r, 0) + mr.get(r, 0)), 3)} for r in set(fr) | set(mr)]
    rows = sorted(rows, key=lambda x: -(x["female_count"] + x["male_count"]))[:60]
    return {"faers_female_share": round(f / (f + m), 3), "adverse_events_by_sex": rows, "faers_reports_total": f + m}

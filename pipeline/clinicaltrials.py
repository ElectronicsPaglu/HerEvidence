"""ClinicalTrials.gov API v2. Computes trial counts, sex restriction, pregnancy-exclusion share and
(where results are posted) female enrolment share. Field names follow the v2 docs; verify on first run."""
import re
from .http import get_json

BASE = "https://clinicaltrials.gov/api/v2/studies"
PREG_RE = re.compile(r"pregnan|breast-?feed|lactating|nursing mother", re.I)

def _page(params, max_pages=3):
    studies, total, token = [], None, None
    for _ in range(max_pages):
        p = dict(params, **({"pageToken": token} if token else {}))
        data = get_json(BASE, p)
        if not data and "fields" in p:                       # retry without field filter if API rejected it
            p.pop("fields"); data = get_json(BASE, p)
        if not data: break
        studies += data.get("studies", [])
        total = data.get("totalCount", total)
        token = data.get("nextPageToken")
        if not token: break
    return studies, total

def excludes_pregnancy(criteria: str) -> bool:
    """Heuristic: does the EXCLUSION part of the criteria mention pregnancy/lactation?"""
    if not criteria: return False
    parts = re.split(r"exclusion criteria", criteria, flags=re.I)
    text = parts[-1] if len(parts) > 1 else criteria
    return bool(PREG_RE.search(text))

def female_share_from_results(studies):
    f = m = 0.0
    for s in studies:
        for meas in s.get("resultsSection", {}).get("baselineCharacteristicsModule", {}).get("measures", []):
            title = (meas.get("title") or "").lower()
            if not ("sex" in title or "gender" in title): continue
            if "participant" not in (meas.get("unitOfMeasure") or "").lower(): continue
            for cls in meas.get("classes", []):
                for cat in cls.get("categories", []):
                    t = (cat.get("title") or "").lower()
                    for mm in cat.get("measurements", []):
                        try: v = float(mm.get("value"))
                        except (TypeError, ValueError): continue
                        if t.startswith("female") or t == "women": f += v
                        elif t.startswith("male") or t == "men": m += v
    return round(100 * f / (f + m), 1) if (f + m) > 0 else None

def fetch(drug):
    studies, total = _page({"query.intr": drug, "pageSize": 100, "countTotal": "true"})
    n = len(studies)
    if n == 0:
        return {}
    ps = lambda s: s.get("protocolSection", {}).get("eligibilityModule", {})
    excl = sum(excludes_pregnancy(ps(s).get("eligibilityCriteria", "")) for s in studies)
    fem = sum(ps(s).get("sex") == "FEMALE" for s in studies)
    male = sum(ps(s).get("sex") == "MALE" for s in studies)
    _, preg_total = _page({"query.intr": drug, "query.cond": "pregnancy", "pageSize": 1, "countTotal": "true"}, 1)
    res_studies, _ = _page({"query.intr": drug, "aggFilters": "results:with", "pageSize": 50, "countTotal": "true"}, 1)
    return {"trials_total": total or n, "pregnancy_trials": preg_total or 0,
            "pregnancy_exclusion_pct": round(100 * excl / n, 1), "female_only_pct": round(100 * fem / n, 1),
            "male_only_pct": round(100 * male / n, 1), "female_enrollment_pct": female_share_from_results(res_studies),
            "ct_sample_size": n}

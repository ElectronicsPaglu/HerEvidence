"""HerEvidence API (Member A). Run: uvicorn app.main:app --reload --port 8000   |  Docs: /docs"""
import os, hashlib, datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel
from . import core, scoring, symptoms, sideeffects, pillcheck, signals, registry, db

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(_):
    registry.seed_if_empty()
    yield

app = FastAPI(title="HerEvidence API", version="1.0", lifespan=lifespan,
              description="Decision support only. Evidence scores measure data availability, not safety.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
SALT = os.getenv("HASH_SALT", "change-me")
DISCLAIMER = "Decision support, not medical advice. Never stop a prescribed medicine without talking to your doctor."


@app.get("/", include_in_schema=False)
def app_ui(): return FileResponse(Path(__file__).resolve().parent.parent / "static" / "index.html")

def uhash(user_id): return hashlib.sha256((SALT + user_id).encode()).hexdigest()[:16]

@app.get("/health")
def health(): return {"status": "ok", "drugs": len(core.DRUGS)}

# ---------------- Module 1: GapRx ----------------
@app.get("/drugs")
def list_drugs():
    return [{"name": d["generic_name"], "aliases": d.get("aliases", []), "class": d["drug_class"]} for d in core.DRUGS]

@app.get("/drug/{name}")
def get_drug(name: str):
    d = core.find_drug(name)
    if not d:
        raise HTTPException(404, f"No data held for '{name}'. Try the generic name.")
    score, label, comps = scoring.evidence_score(d)
    expl = scoring.explain(d)
    alts = pillcheck.rank_alternatives(d["alternatives_goal"])[:3] if d.get("alternatives_goal") else []
    return {
        "name": d["generic_name"], "drugClass": d["drug_class"], "aliases": d.get("aliases", []),
        "evidenceScore": score, "evidenceLabel": label, "components": comps,
        "scoreNote": "This score reflects how much evidence exists for women. It is not a safety rating.",
        "pregnancyData": {"score": comps["pregnancy"], "summary": expl["pregnancy"], "trialsStudyingPregnancy": d.get("pregnancy_trials"),
                          "trialsSampledExcludingPregnancyPct": d.get("pregnancy_exclusion_pct"),
                          "labelHasHumanData": bool(d.get("label_has_human_pregnancy_data")), "labelNote": d.get("label_pregnancy_note")},
        "breastfeedingData": {"score": comps["breastfeeding"], "summary": expl["breastfeeding"], "labelHasLactationData": bool(d.get("label_has_lactation_data")),
                              "papers": d.get("lactation_papers")},
        "sexSpecificData": {"score": comps["sex_specific"], "summary": expl["sex_specific"], "femaleEnrollmentPct": d.get("female_enrollment_pct"),
                            "dosingNote": d.get("sex_specific_dosing_note")},
        "sexSpecificEffects": sorted([e for e in d.get("adverse_events_by_sex", [])], key=lambda e: -e["female_share"])[:8],
        "faersFemaleSharePct": round(d.get("faers_female_share", 0) * 100),
        "alternatives": alts, "sources": d["sources"], "dataOrigin": d.get("data_origin"),
        "dataOriginNote": "Illustrative demo values." if d.get("data_origin") == "demo_seed" else f"Retrieved {d.get('retrieved_on')} from public APIs.",
        "disclaimer": DISCLAIMER}

class RegistryIn(BaseModel):
    userId: str
    drug: str
    trimester: int
    outcome: str
    consent: bool

@app.post("/registry/entries")
def add_registry(e: RegistryIn):
    if not e.consent: raise HTTPException(400, "Explicit consent is required.")
    if e.trimester not in (1, 2, 3): raise HTTPException(400, "trimester must be 1, 2 or 3")
    with db.conn() as c:
        c.execute("INSERT INTO registry_entries(user_hash,drug,trimester,outcome,entry_date,is_simulated,consent) VALUES (?,?,?,?,?,0,1)",
                  (uhash(e.userId), e.drug.lower(), e.trimester, e.outcome, datetime.date.today().isoformat()))
    return {"saved": True, "note": "Stored anonymised (hashed id). Opt-in registry."}

@app.get("/registry/signals")
def registry_signals(trimester: Optional[int] = Query(None, ge=1, le=3), include_all: bool = False):
    with db.conn() as c:
        rows = [dict(r) for r in c.execute("SELECT drug,trimester,outcome,is_simulated FROM registry_entries")]
    # no trimester given -> scan pooled data AND each trimester separately (signals can hide when pooled)
    strata = [trimester] if trimester else [None, 1, 2, 3]
    res = [r for t in strata for r in signals.analyse(rows, t)]
    res.sort(key=lambda x: (not x["flagged"], -x["prr"]))
    flagged = [r for r in res if r["flagged"]]
    return {"isSimulated": any(r["is_simulated"] for r in rows), "entries": len(rows), "testsRun": len(res), "flaggedCount": len(flagged),
            "signals": res if include_all else flagged,
            "multipleTestingNote": "Many drug x outcome x trimester combinations are tested, so some flags can arise by chance. Treat each as a question to investigate.",
            "interpretation": "A flagged signal is a hypothesis for clinical/regulatory review, not proof of causation. Data shown is SIMULATED."}

@app.get("/registry/report")
def registry_report(drug: str, trimester: Optional[int] = Query(None, ge=1, le=3)):
    with db.conn() as c:
        rows = [dict(r) for r in c.execute("SELECT drug,trimester,outcome FROM registry_entries")]
    items = [r for r in signals.analyse(rows, trimester) if r["drug"].lower() == drug.lower() and r["flagged"]]
    if not items:
        text = f"No disproportionate outcome clusters were flagged for {drug} in this dataset."
    else:
        text = "\n".join(f"- {r['outcome'].replace('_', ' ')}: PRR {r['prr']}, ROR {r['ror']} (95% CI {r['rorCI95'][0]}-{r['rorCI95'][1]}), "
                         f"chi-square {r['chi2']}, {r['a']} reports." for r in items)
    return {"report": f"SIMULATED-DATA SIGNAL REPORT for {drug}\n{text}\nA signal is a hypothesis for review, not proof of causation.", "isSimulated": True}

# ---------------- Module 2: Atypical presentation ----------------
class SymptomIn(BaseModel):
    text: Optional[str] = None
    symptomIds: Optional[List[str]] = None

@app.get("/symptoms/vocabulary")
def vocab(): return [{"id": s["id"], "label": s["label"]} for s in core.SYMPTOMS]

@app.post("/symptoms/match")
def symptoms_match(b: SymptomIn):
    ids = list(b.symptomIds or [])
    if b.text: ids += symptoms.map_text(b.text)
    if not ids: raise HTTPException(400, "Provide text or symptomIds.")
    return symptoms.match(ids)

# ---------------- Module 3: Side-effect detector ----------------
class SideIn(BaseModel):
    medicines: List[str]
    symptomIds: Optional[List[str]] = None
    text: Optional[str] = None

@app.post("/sideeffects/check")
def side_check(b: SideIn):
    ids = list(b.symptomIds or [])
    if b.text: ids += symptoms.map_text(b.text)
    if not b.medicines or not ids: raise HTTPException(400, "Provide medicines and symptoms.")
    return sideeffects.check(b.medicines, list(dict.fromkeys(ids)))

# ---------------- Module 4: Pill Check ----------------
class ScoreIn(BaseModel):
    phq9Items: Optional[List[int]] = None
    phq9Total: Optional[int] = None
    gad7Items: Optional[List[int]] = None
    gad7Total: Optional[int] = None
    baselinePhq9: Optional[int] = None
    baselineGad7: Optional[int] = None

@app.post("/pillcheck/score")
def pill_score(b: ScoreIn):
    try:
        return pillcheck.score(b.phq9Items, b.phq9Total, b.gad7Items, b.gad7Total, b.baselinePhq9, b.baselineGad7)
    except ValueError as ex:
        raise HTTPException(400, str(ex))

class MoodIn(BaseModel):
    userId: str
    date: Optional[str] = None
    phq9Items: Optional[List[int]] = None
    phq9Total: Optional[int] = None
    gad7Items: Optional[List[int]] = None
    gad7Total: Optional[int] = None
    pillEvent: Optional[str] = None

@app.post("/pillcheck/entries")
def pill_entry(b: MoodIn):
    try:
        s = pillcheck.score(b.phq9Items, b.phq9Total, b.gad7Items, b.gad7Total)
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    with db.conn() as c:
        c.execute("INSERT INTO mood_entries(user_hash,entry_date,phq9,gad7,pill_event,is_simulated) VALUES (?,?,?,?,?,0)",
                  (uhash(b.userId) if b.userId != "demo_user" else "demo_user", b.date or datetime.date.today().isoformat(),
                   s.get("phq9", {}).get("total"), s.get("gad7", {}).get("total"), b.pillEvent))
    return s

@app.get("/pillcheck/trend/{user_id}")
def pill_trend(user_id: str):
    h = "demo_user" if user_id == "demo_user" else uhash(user_id)
    with db.conn() as c:
        rows = c.execute("SELECT * FROM mood_entries WHERE user_hash=? ORDER BY entry_date,id", (h,)).fetchall()
    if not rows: raise HTTPException(404, "No entries yet.")
    return pillcheck.trend(rows)

@app.get("/pillcheck/alternatives")
def alternatives(goal: str = Query(..., description="contraception | pcos | acne | heavy_bleeding")):
    goal = goal.lower()
    if goal not in ("contraception", "pcos", "acne", "heavy_bleeding"):
        raise HTTPException(400, "goal must be contraception, pcos, acne or heavy_bleeding")
    return {"goal": goal, "methods": pillcheck.rank_alternatives(goal), "accuracyNotes": core.ALTERNATIVES["accuracy_notes"], "disclaimer": DISCLAIMER}

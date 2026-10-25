# HerEvidence: "Was this studied on her?"
Medicine was built on male bodies. HerEvidence shows women where the evidence ends: an Evidence Score for Women for any drug,
a female-vs-textbook symptom comparison, a side-effect vs disease detector, and a hormonal-contraception mood tracker.
**Decision support only. Not medical advice. No "safe/unsafe" verdicts.**

## For judges: try it in under a minute
**Live demo:** `PASTE-YOUR-RENDER-URL-HERE` (free hosting: the first load can take ~30-60 seconds to wake up)

Suggested 3-minute path: GapRx (search "zolpidem" or "Ambien") -> Symptoms (tap jaw pain + nausea + fatigue) -> Side effects (pill + low mood)
-> Pill Check (demo user mood chart, alternatives) -> Card (export PDF). API docs: `<live-url>/docs`

**Run it yourself** (any one of these):
```bash
# Option 1: Python 3.9+
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000        # open http://localhost:8000

# Option 2: Docker
docker build -t herevidence . && docker run -p 8000:8000 herevidence
```
Tests: `pip install -r requirements-dev.txt && python -m pytest -q tests`

**Team split:** Member A = data, scoring, detection logic, API (`app/`, `pipeline/`, `data/`). Member B = app UX/design (`static/index.html`).

---

## Technical notes (backend)

## What this is (plain English)
A small web server. Member B's app sends it a question ("tell me about zolpidem", "I have these symptoms")
and it replies with JSON. Inside: a score for how much evidence exists for women, a symptom matcher,
a side-effect checker, a mood-score calculator, and a detector that finds unusual patterns in (simulated) registry data.

## The whole project in one command (backend + Member B's app)
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- App (Member B's UI, wired to the API): http://localhost:8000/
- API docs (try endpoints): http://localhost:8000/docs
- On your phone (same Wi-Fi): http://YOUR-LAPTOP-IP:8000/  or use `ngrok http 8000` for a public https link.
- `static/index.html` is Member B's design with live data. Edit it for UI changes and refresh the browser; there is no build step.

## Run it (5 minutes)
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000/docs : an interactive page where you can try every endpoint.
To let Member B's phone reach it: `ngrok http 8000` and share the https URL (or deploy on Render/Railway).
Run the tests: `python -m pytest -q tests`

## IMPORTANT: what is real and what is a placeholder
| Item | Status |
|---|---|
| Drug numbers in `data/drugs.json` | **DEMO SEED = illustrative placeholders, not real measurements.** Replace with real data using the pipeline (below). Every drug response has `dataOrigin` so the app can show this. |
| Pipeline (`pipeline/`) | Written but **not yet run against the real APIs** (my build environment had no internet). First run may need small field-name fixes; it is the first thing to do. |
| Registry data | Simulated on purpose, with **fictional** drug names (DemoDrug-A..E) and one injected signal. |
| Conditions, alternatives, cascades | Written from general medical knowledge with starting-point sources. All marked `needs_review`. **You must check each claim against its source** (see claims register). |
| Crisis helplines, PHQ-9/GAD-7 thresholds, failure rates | Verify before the demo. |

## Get real data (do this first): fast version
```
python -m pipeline.run_pipeline --csv data/drug_list.csv
```
Pulls ~80 drugs (list in `data/drug_list.csv`; add your own rows). Takes 10-25 min; progress is saved after every drug and
responses are cached, so you can stop/re-run safely. Optional: set `OPENFDA_API_KEY` first (PowerShell: `$env:OPENFDA_API_KEY="your-key"`).

## Get real data: details
1. (Optional) free API keys: openFDA and NCBI; copy `.env.example` to `.env`.
2. `python -m pipeline.run_pipeline`  (refreshes the 10 seed drugs; takes a few minutes; results cached in `data/cache/`)
3. Add more: `python -m pipeline.run_pipeline --drugs naproxen,fluoxetine,topiramate`
   (for a new drug, also open `data/drugs.json` and fill `drug_class` and `aliases`)
4. Look at the output in `data/drugs.json`; check `data_origin` says `live_pipeline`. Sanity-check numbers on the websites.
5. `python scripts/export_claims.py` writes `docs/claims_register.csv`: every claim + source. Fill it in / verify it.

## Folder map
- `app/main.py`: all API endpoints
- `app/scoring.py`: Evidence Score (formula in the file header; it measures data availability, NOT safety)
- `app/signals.py`: PRR / ROR / chi-square signal detector (Evans criteria)
- `app/registry.py`: simulated registry generator (+ demo mood story for `demo_user`)
- `app/symptoms.py`: symptom text -> vocabulary -> condition matching (plain code; LLM optional)
- `app/sideeffects.py`: label + sex-split FAERS cross-check, confidence rules, hard-coded wording, cascades
- `app/pillcheck.py`: PHQ-9/GAD-7 scoring, change detection, crisis flag, alternatives ranking
- `app/llm.py`: optional Claude helper (only maps text to our fixed symptom list; falls back to keywords)
- `pipeline/`: ClinicalTrials.gov, openFDA (labels + FAERS), PubMed fetchers
- `data/*.json`: the "Women Evidence Database": drugs, symptoms, conditions, cascades, alternatives
- `docs/sample_responses.json`: real example responses: **give this to Member B as the API contract / mock data**

## Endpoints
| Endpoint | Purpose |
|---|---|
| `GET /drug/{name}` | Evidence score, components, pregnancy/breastfeeding/sex data, sex-split side effects, alternatives, sources |
| `GET /drugs` | Names for search suggestions |
| `POST /symptoms/match` `{text?, symptomIds?}` | Conditions that commonly present this way + questions for doctor |
| `GET /symptoms/vocabulary` | Symptom chips for the UI |
| `POST /sideeffects/check` `{medicines[], symptomIds[]?, text?}` | Flags with confidence + fixed wording, cascades, dosing notes |
| `POST /pillcheck/score` | PHQ-9/GAD-7 totals, bands, change, `crisisFlag` + helplines |
| `POST /pillcheck/entries`, `GET /pillcheck/trend/{userId}` | Save mood entries; trend with medicine marker + alert. Try `demo_user` |
| `GET /pillcheck/alternatives?goal=` | contraception / pcos / acne / heavy_bleeding |
| `GET /registry/signals`, `GET /registry/report?drug=` | Signal dashboard + report text (simulated) |
| `POST /registry/entries` | Opt-in registry entry (requires `consent: true`) |

## Safety rules built into the code
No "safe/unsafe" wording; no "stop taking"; confidence + wording are fixed templates (tests check this);
crisis flag if PHQ-9 item 9 > 0 or total >= 20; red-flag emergency message in symptom matcher;
FAERS caveats returned in every side-effect response; evidence score labelled as not a safety rating.

## Known limitations (say these in the pitch, it shows rigour)
- FAERS = voluntary reports: no causation, no incidence. Female-share can reflect who reports/who takes the drug.
- ClinicalTrials pregnancy-exclusion % is a keyword heuristic on a sample of up to 300 trials per drug.
- Symptom matcher is overlap-scoring, not diagnosis. Signal flags across many tests can arise by chance.
- No user authentication yet: demo only. Add auth before any real use.

# HerEvidence: "Was this studied on her?"

> Medicine was built on male bodies. HerEvidence shows women where the evidence ends.

HerEvidence is a mobile-first web app that makes the **absence of evidence** visible. For any medicine it shows how much was ever studied in women (pregnancy, breastfeeding, sex-specific data). It also compares how conditions present in women versus the textbook, flags possible side effects, and tracks mood around hormonal contraception.

**Decision support only. Not medical advice. HerEvidence never gives "safe" or "unsafe" verdicts, never diagnoses, and never tells anyone to stop a medicine.**

**Live app:** https://herevidence.onrender.com/ (on free hosting the first load can take up to a minute to wake up)
**API docs:** https://herevidence.onrender.com/docs

\---

## Why this exists

* **Pregnancy evidence gap.** Only 0.8% of 90,860 drug trials included pregnant participants, and about 75% excluded them (Brown University / AJOG, 2025).
* **Diagnosis gap.** Across 770 diseases, women are diagnosed about 4 years later than men on average (Westergaard et al., *Nature Communications*, 2019). Young women's heart attack symptoms are more often dismissed as non-cardiac (Yale / *Circulation*, 2018).
* **Side-effect gap.** Women experience adverse drug reactions nearly twice as often, partly because doses were set on male-dominated trials (Zucker and Prendergast, 2020). The FDA halved the recommended zolpidem (Ambien) starting dose for women in 2013.
* **Contraception and mood.** A Danish cohort of over 1 million women found hormonal contraception associated with later antidepressant use and depression diagnoses, especially in adolescents (Skovlund et al., *JAMA Psychiatry*, 2016). This is an association, and the absolute risk is small, but individual response varies and is rarely tracked.

## Features

|Module|What it does|
|-|-|
|**GapRx**|Search a medicine (brand or generic) to get an **Evidence Score for Women** with separate pregnancy, breastfeeding and sex-specific components, sex-split reported effects, sources, and an opt-in anonymised exposure registry with a signal dashboard.|
|**Atypical Presentation Engine**|Tap, type or speak symptoms. See textbook versus female presentation for 20 commonly missed conditions, the tests that are often skipped, and a "questions to ask your doctor" list. Urgent patterns (for example the heart-attack pattern) show an emergency warning.|
|**Side-Effect vs Disease Detector**|Log a medicine and a symptom. It cross-checks label data and sex-split adverse-event reports, rates confidence (higher, moderate or lower), and uses fixed cautious wording. It flags known prescribing cascades and sex-specific dosing notes.|
|**Pill Check**|PHQ-9 and GAD-7 tracking before and after a hormonal contraceptive, a trend chart with a "pill started" marker, an immediate crisis-support screen, and an **Alternatives Navigator** ranking options by goal (contraception, PCOS, acne, heavy bleeding).|
|**Doctor card**|A one-page PDF of questions, mood trend and flagged items to bring to an appointment.|

All modules share one **Women Evidence Database**. A mood rise in Pill Check links straight to the side-effect check, and a drug page shows its pregnancy data, sex-specific effects and alternatives in one view.

## Quick tour

1. **GapRx:** search `zolpidem` (or `Ambien`) to see the score, the pregnancy gap and the sex-specific dosing note.
2. **Symptoms:** tap *jaw pain*, *nausea*, *fatigue* to see the female-presentation comparison and the urgent banner.
3. **Side effects:** pick *the pill* and *low mood* to see the confidence rating and careful wording.
4. **Pill Check:** open the sample user's mood chart and the alternatives, then export the doctor card from the **Card** tab.

## Getting started

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Open http://localhost:8000 for the app, or http://localhost:8000/docs for the interactive API.

A `Dockerfile` is also included: `docker build -t herevidence . \&\& docker run -p 8000:8000 herevidence`

Run the tests: `pip install -r requirements-dev.txt \&\& python -m pytest -q tests`

### Refreshing the drug data

The repository already contains the pulled data in `data/drugs.json`. To refresh it or add medicines you need a **free openFDA API key** (https://open.fda.gov/apis/authentication/), because the adverse-event endpoint refuses requests without one:

```powershell
$env:OPENFDA\_API\_KEY="your-key"          # PowerShell; on Mac/Linux: export OPENFDA\_API\_KEY=your-key
python -m pipeline.run\_pipeline --csv data/drug\_list.csv
```

Add medicines as rows in `data/drug\_list.csv`. Responses are cached and progress is saved after every drug. Never commit your key; `.env` is git-ignored.

### Configuration

|Variable|Purpose|
|-|-|
|`OPENFDA\_API\_KEY`|Required only when running the data pipeline|
|`NCBI\_API\_KEY`|Optional, raises PubMed rate limits|
|`ANTHROPIC\_API\_KEY`|Optional, improves free-text symptom mapping (the app works without it)|
|`HASH\_SALT`|Salt used to hash registry and mood user IDs|

## Architecture

```
ClinicalTrials.gov ─┐
openFDA labels  ────┼─> pipeline/ ─> data/drugs.json ─┐
openFDA FAERS ──────┤                                 │
PubMed ─────────────┘   curated JSON (conditions,     ├─> FastAPI (app/) ─> mobile web app (static/)
                        alternatives, cascades) ──────┘
```

* **Evidence Score** (`app/scoring.py`): three documented components, pregnancy (40%), breastfeeding (20%) and sex-specific data (40%), each built from trial counts, pregnancy-exclusion share, label content, paper counts and female enrolment. It measures **how much data exists, not how safe a drug is**. The formula is in the file header.
* **Signal detector** (`app/signals.py`): disproportionality analysis (PRR, ROR with 95% CI, Yates-corrected chi-square, Evans criteria) on a registry. A flagged signal is a hypothesis for review, not proof of causation.
* **Symptom matcher** (`app/symptoms.py`): maps text onto a fixed vocabulary of 63 symptoms, then scores conditions by weighted overlap in plain code. Weak matches are labelled as weak.
* **Side-effect checker** (`app/sideeffects.py`): confidence is *higher* if the effect is on the label and women are over-represented in reports, *moderate* if on the label only, and *lower* if in reports only. Wording is fixed templates.
* **Optional LLM** (`app/llm.py`): if `ANTHROPIC\_API\_KEY` is set, it only helps map free text onto the fixed symptom list. It never supplies facts or verdicts.

## API

|Endpoint|Purpose|
|-|-|
|`GET /drug/{name}`|Evidence score, components, pregnancy, breastfeeding and sex data, sex-split reported effects, alternatives, sources|
|`GET /drugs`|Medicine names and aliases for search|
|`POST /symptoms/match`|Conditions that commonly present this way, with questions for a doctor|
|`GET /symptoms/vocabulary`|Symptom list|
|`POST /sideeffects/check`|Flags with confidence and fixed wording, cascades, dosing notes|
|`POST /pillcheck/score`|PHQ-9 and GAD-7 totals, bands, change, crisis flag and helplines|
|`POST /pillcheck/entries`, `GET /pillcheck/trend/{userId}`|Save mood entries and view the trend with a medicine marker|
|`GET /pillcheck/alternatives?goal=`|`contraception`, `pcos`, `acne` or `heavy\_bleeding`|
|`GET /registry/signals`, `GET /registry/report?drug=`|Signal dashboard and report text|
|`POST /registry/entries`|Opt-in registry entry (requires `consent: true`)|

Example responses are in `docs/sample\_responses.json`.

## Data: what is real, what is simulated

|Data|Source and status|
|-|-|
|Drug evidence (82 medicines)|Pulled by `pipeline/` from ClinicalTrials.gov, openFDA labels and FAERS, and PubMed. Each record carries `data\_origin` and `retrieved\_on`.|
|Conditions, alternatives, prescribing cascades|Curated from public health sources (NHS, WHO, AHA and others). **Every claim and its source link is listed in `docs/claims\_register.csv`.** Not clinically validated.|
|Pregnancy exposure registry|**Simulated** and clearly labelled, using **fictional** drug names (`DemoDrug-A` to `E`) with one deliberately injected signal to show how the detector works.|
|Sample mood user (`demo\_user`)|**Simulated** to demonstrate the Pill Check flow.|

## Safety and ethics

* No diagnosis and no safe/unsafe verdicts. Every screen carries a decision-support disclaimer.
* Wording never tells a user to stop or change a medicine; it says to discuss with a doctor (checked by tests).
* Crisis screen if PHQ-9 item 9 is above 0 or the total is 20 or more, with helplines. Emergency warning for urgent symptom patterns.
* Registry participation is opt-in, requires explicit consent, and stores a salted hash instead of an identity.
* The evidence score is labelled everywhere as a data-availability measure.
* Accuracy note built into the app: the pill raises *total* cortisol mainly via binding proteins, while *free* cortisol is usually not elevated.

## Limitations

* FAERS is voluntary, unverified reporting: it cannot prove causation or give incidence. Female share of reports can reflect who takes a drug and who reports.
* The trial pregnancy-exclusion percentage is a keyword heuristic on a sample of trials per drug.
* The symptom matcher is overlap scoring, not diagnosis. Many signal tests run at once, so some flags can arise by chance.
* Helpline numbers shown are for India; verify them for other regions.
* No user accounts or authentication yet. On free hosting the local registry resets on restart.
* This is a prototype, not a medical device, and it has not been validated in clinical use.

## Project structure

```
app/        FastAPI backend: scoring, signals, symptom matcher, side-effect checker, Pill Check, API
pipeline/   Data fetchers for ClinicalTrials.gov, openFDA and PubMed
data/       Women Evidence Database (JSON) and drug list
static/     Mobile-first web app (single page)
scripts/    Claims exporter, data and API checks
tests/      Unit and API tests
docs/       Claims register and sample API responses
```

## Contributors

|Name|Role|
|-|-|
|**Vanshika Malik**|Data and AI: pipeline, database, scoring, detection logic, API|
|**Aakanksha Sharma**|App and UX: design, user flows, app interface|

## References

* Pregnant women in drug trials (Brown University, 2025): https://www.brown.edu/news/2025-01-17/pregnant-study-participants
* National Academies report coverage (The Fuller Project, 2024): https://archive.fullerproject.org/?p=13571
* Frances Kelsey and thalidomide (NLM): https://nlm.nih.gov/exhibition/changing-the-face-of-medicine/physicians/biography\_frances\_kelsey.html
* Women diagnosed later than men (*Nature Communications*, 2019): https://www.cpr.ku.dk/cprnews/2019/study-across-diseases-women-are-diagnosed-later-than-men
* Younger women's heart attack symptoms (Yale, 2018): https://news.yale.edu/2018/02/19/heart-attack-symptoms-often-misinterpreted-younger-women
* Sex differences and adverse drug reactions (UC Berkeley, 2020): https://news.berkeley.edu/2020/08/12/lack-of-females-in-drug-dose-trials-leads-to-overmedicated-women/
* Hormonal contraception and depression (*JAMA Psychiatry*, 2016, DOI 10.1001/jamapsychiatry.2016.2387): https://womensmentalhealth.org/posts/11202/

## License

MIT. See `LICENSE`.

*We don't ask if a drug is safe. We ask: was it ever tested on her?*


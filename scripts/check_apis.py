"""Quick connectivity test for the three public data sources. Run:  python scripts/check_apis.py
Shows the HTTP status and the server's own message for each, with and without your openFDA key."""
import os, requests
KEY = os.getenv("OPENFDA_API_KEY")
H = {"User-Agent": "HerEvidence-hackathon/1.0 (educational project)", "Accept": "application/json"}
EV, LB = "https://api.fda.gov/drug/event.json", "https://api.fda.gov/drug/label.json"
S = 'patient.drug.openfda.generic_name:"sertraline"'
tests = [
 ("openFDA label", LB, {"search": 'openfda.generic_name:"sertraline"', "limit": 1}),
 ("openFDA FAERS plain", EV, {"search": S, "limit": 1}),
 ("openFDA FAERS count (limit 100)", EV, {"search": S, "count": "patient.patientsex", "limit": 100}),
 ("openFDA FAERS count (limit 1000)", EV, {"search": S, "count": "patient.patientsex", "limit": 1000}),
 ("ClinicalTrials.gov", "https://clinicaltrials.gov/api/v2/studies", {"query.intr": "sertraline", "pageSize": 1}),
 ("PubMed", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", {"db": "pubmed", "term": "sertraline AND pregnancy", "retmode": "json", "rettype": "count"}),
]
print("OPENFDA_API_KEY is", "SET" if KEY else "NOT set in this window")
for name, url, params in tests:
    for with_key in ([False, True] if (KEY and name.startswith("openFDA")) else [False]):
        p = dict(params, **({"api_key": KEY} if with_key else {}))
        try:
            r = requests.get(url, params=p, timeout=30, headers=H)
            print(f"{name:36}{' [with key]' if with_key else ' [no key]  ' if name.startswith('openFDA') else '           '} -> {r.status_code}  {r.text[:110].strip()!r}")
        except Exception as e:
            print(f"{name:36} -> FAILED: {e}")

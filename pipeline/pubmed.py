"""PubMed E-utilities: counts of papers per topic (a rough signal of how much research exists)."""
import os
from .http import get_json
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

def count(term):
    p = {"db": "pubmed", "term": term, "retmode": "json", "rettype": "count"}
    if os.getenv("NCBI_API_KEY"): p["api_key"] = os.getenv("NCBI_API_KEY")
    d = get_json(ESEARCH, p, pause=0.35)
    try: return int(d["esearchresult"]["count"])
    except Exception: return None

def fetch(generic):
    return {"pregnancy_papers": count(f'"{generic}"[Title/Abstract] AND pregnancy[Title/Abstract]'),
            "lactation_papers": count(f'"{generic}"[Title/Abstract] AND (lactation OR breastfeeding)[Title/Abstract]'),
            "sex_specific_papers": count(f'"{generic}"[Title/Abstract] AND ("sex differences" OR "sex-specific" OR "sex factors")')}

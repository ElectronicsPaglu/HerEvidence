"""Evidence Score for Women.

IMPORTANT: this is a DATA-AVAILABILITY score, not a safety rating. A low score means
'little was studied in women', never 'unsafe'. A high score never means 'safe'.

Formula (documented so every number can be defended):
  pregnancy     = 0.4*min(1, pregnancy_trials/10) + 0.3*(1 - pregnancy_exclusion_pct/100) + 0.3*label_has_human_pregnancy_data
  breastfeeding = 0.6*label_has_lactation_data     + 0.4*min(1, lactation_papers/20)
  sex_specific  = 0.4*min(1, female_enrollment_pct/50) + 0.3*min(1, sex_specific_papers/50) + 0.3*has_sex_specific_dosing_info
  score = round(100 * (0.40*pregnancy + 0.20*breastfeeding + 0.40*sex_specific))
Missing inputs count as 0 (absence of data lowers the score; that is the point).
"""
WEIGHTS = {"pregnancy": 0.40, "breastfeeding": 0.20, "sex_specific": 0.40}

def _n(x):  # None -> 0
    return float(x) if x is not None else 0.0

def components(d: dict) -> dict:
    preg = (0.4 * min(1, _n(d.get("pregnancy_trials")) / 10)
            + 0.3 * (1 - _n(d.get("pregnancy_exclusion_pct")) / 100 if d.get("pregnancy_exclusion_pct") is not None else 0)
            + 0.3 * (1 if d.get("label_has_human_pregnancy_data") else 0))
    lact = (0.6 * (1 if d.get("label_has_lactation_data") else 0)
            + 0.4 * min(1, _n(d.get("lactation_papers")) / 20))
    sex = (0.4 * min(1, _n(d.get("female_enrollment_pct")) / 50)
           + 0.3 * min(1, _n(d.get("sex_specific_papers")) / 50)
           + 0.3 * (1 if d.get("has_sex_specific_dosing_info") else 0))
    return {"pregnancy": round(preg, 3), "breastfeeding": round(lact, 3), "sex_specific": round(sex, 3)}

def label_for(score: int) -> str:
    if score < 35: return "Limited evidence in women"
    if score < 65: return "Moderate evidence in women"
    return "Substantial evidence in women"

def evidence_score(d: dict):
    c = components(d)
    score = round(100 * sum(WEIGHTS[k] * c[k] for k in WEIGHTS))
    return score, label_for(score), c

def explain(d: dict) -> dict:
    """Plain-language gap sentences for the UI (generated from numbers, never free-styled)."""
    out = {}
    ex = d.get("pregnancy_exclusion_pct")
    out["pregnancy"] = (f"In the {d.get('trials_total', 'N/A')} registered trials found, about {ex:.0f}% of sampled trials listed pregnancy "
                        f"as an exclusion; {d.get('pregnancy_trials', 0)} trials were found that studied pregnancy."
                        if ex is not None else "Trial exclusion data not available.")
    out["breastfeeding"] = ("The label contains lactation information." if d.get("label_has_lactation_data")
                            else "No lactation information found in the label data we hold.")
    fe = d.get("female_enrollment_pct")
    out["sex_specific"] = (f"About {fe:.0f}% of participants in trials with posted results were women. " if fe is not None else "")\
        + ("Sex-specific dosing information exists." if d.get("has_sex_specific_dosing_info") else "No sex-specific dosing information found.")
    return out

"""Pharmacovigilance disproportionality analysis (PRR / ROR / chi-square, Evans criteria).
A flagged signal is a HYPOTHESIS FOR REVIEW, not proof of causation."""
import math

def signal(a, b, c, d):
    """2x2 table: a=exposed&outcome, b=exposed&no outcome, c=unexposed&outcome, d=unexposed&no outcome."""
    n = a + b + c + d
    chi2 = 0.0
    denom = (a + b) * (c + d) * (a + c) * (b + d)
    if denom > 0:
        chi2 = ((abs(a * d - b * c) - n / 2) ** 2 * n) / denom   # Yates-corrected
    # Haldane-Anscombe correction only if a zero cell would break the ratios
    A, B, C, Dd = (a, b, c, d) if min(a, b, c, d) > 0 else (a + .5, b + .5, c + .5, d + .5)
    prr = (A / (A + B)) / (C / (C + Dd))
    ror = (A * Dd) / (B * C)
    se = math.sqrt(1 / A + 1 / B + 1 / C + 1 / Dd)
    lo, hi = math.exp(math.log(ror) - 1.96 * se), math.exp(math.log(ror) + 1.96 * se)
    flagged = prr >= 2 and chi2 >= 4 and a >= 3        # Evans et al. criteria
    return {"a": a, "b": b, "c": c, "d": d, "prr": round(prr, 2), "ror": round(ror, 2),
            "rorCI95": [round(lo, 2), round(hi, 2)], "chi2": round(chi2, 2), "flagged": flagged}

def analyse(rows, trimester=None, no_outcome="no_complication"):
    """rows: list of dicts with drug, trimester, outcome. Returns one result per drug x outcome."""
    drugs = sorted({r["drug"] for r in rows})
    outcomes = sorted({r["outcome"] for r in rows} - {no_outcome})
    results = []
    for drug in drugs:
        exposed = [r for r in rows if r["drug"] == drug and (trimester is None or r["trimester"] == trimester)]
        unexposed = [r for r in rows if r["drug"] != drug]
        for oc in outcomes:
            a = sum(r["outcome"] == oc for r in exposed); b = len(exposed) - a
            c = sum(r["outcome"] == oc for r in unexposed); d = len(unexposed) - c
            if a + b == 0: continue
            results.append({"drug": drug, "outcome": oc, "trimester": trimester, **signal(a, b, c, d)})
    results.sort(key=lambda x: (not x["flagged"], -x["prr"]))
    return results

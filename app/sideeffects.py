"""Module 3: cross-check logged medicines x symptoms against label + sex-split FAERS data.
Confidence: higher = on label AND women over-represented; moderate = on label; lower = reports only.
FAERS is voluntary, unverified reporting: it cannot prove causation or give incidence."""
from . import core

ELEVATION_MARGIN = 0.05      # female share must exceed the drug's overall female share by 5 points
MIN_REPORTS = 30             # ignore tiny counts

def _label_hit(drug, sym):
    terms = {t.lower() for t in sym.get("faers_terms", [])} | {sym["label"].lower()} | set(sym["synonyms"])
    label_terms = set(drug.get("label_adverse_terms", []))
    return any(t in label_terms or any(t == x or t in x or x in t for x in label_terms) for t in terms if len(t) > 3)

def _wording(conf, sym, drug, pct, overall, informative):
    s, d = sym["label"], drug["generic_name"]
    if conf == "higher":
        return (f"{s} is a reported side effect of {d} (it appears in the product label data). In adverse-event reports it is "
                f"proportionally more common in women ({pct}% of reports versus {overall}% of all reports for this medicine). "
                f"This is a pattern in reports, not proof of cause. Discuss with your doctor.")
    if conf == "moderate":
        extra = "" if informative else " Sex comparison is not informative because almost all reports for this medicine are from women."
        return f"{s} is a reported side effect of {d} (it appears in the product label data).{extra} Discuss with your doctor."
    return (f"{s} appears in voluntary adverse-event reports for {d}, but we did not find it in the label data we hold. "
            f"Reports cannot show cause. Discuss with your doctor if it bothers you.")

def check(medicines, symptom_ids):
    flags, unmatched, dosing, no_data = [], [], [], []
    resolved = []
    for m in medicines:
        drug = core.find_drug(m)
        if not drug:
            unmatched.append(m); continue
        resolved.append(drug)
        if drug.get("has_sex_specific_dosing_info") and drug.get("sex_specific_dosing_note"):
            dosing.append({"drug": drug["generic_name"], "note": drug["sex_specific_dosing_note"], "sources": drug["sources"]})
    covered = set()
    for drug in resolved:
        overall = drug.get("faers_female_share")
        informative = overall is not None and overall < 0.95
        for sid in symptom_ids:
            sym = core.SYMPTOM_BY_ID.get(sid)
            if not sym: continue
            terms = {t.upper() for t in sym.get("faers_terms", [])}
            faers = [e for e in drug.get("adverse_events_by_sex", []) if e["reaction"].upper() in terms]
            label = _label_hit(drug, sym)
            if not faers and not label:
                continue
            covered.add(sid)
            best = max(faers, key=lambda e: e["female_count"] + e["male_count"], default=None)
            reports = (best["female_count"] + best["male_count"]) if best else 0
            elevated = bool(best and informative and reports >= MIN_REPORTS and best["female_share"] >= overall + ELEVATION_MARGIN)
            conf = "higher" if (label and elevated) else "moderate" if label else "lower"
            pct = round(best["female_share"] * 100) if best else None
            flags.append({"symptom": sym["label"], "symptomId": sid, "drug": drug["generic_name"], "confidence": conf,
                          "onLabel": label, "femaleReportShareElevated": elevated,
                          "femaleReportSharePct": pct, "overallFemaleSharePct": round(overall * 100) if overall is not None else None,
                          "wording": _wording(conf, sym, drug, pct, round((overall or 0) * 100), informative),
                          "alsoConsider": "Symptoms can also have causes unrelated to medicines. See the Symptoms tab for conditions that can present this way.",
                          "dataOrigin": drug.get("data_origin"), "sources": drug["sources"]})
    order = {"higher": 0, "moderate": 1, "lower": 2}
    flags.sort(key=lambda f: order[f["confidence"]])
    for sid in symptom_ids:
        if sid in core.SYMPTOM_BY_ID and sid not in covered:
            no_data.append({"symptom": core.SYMPTOM_BY_ID[sid]["label"],
                            "message": "No matching label or sex-specific report data found for your medicines. This does not mean it is unrelated."})
    # prescribing cascades (curated list)
    haystack = " ".join([m.lower() for m in medicines] + [f"{d['generic_name']} {d['drug_class']}".lower() for d in resolved])
    cascades = [{"id": c["id"], "description": c["description"], "wording": "This combination can sometimes reflect a prescribing cascade. Discuss with your doctor whether it is still needed.",
                 "sources": c["sources"]}
                for c in core.CASCADES
                if any(t in haystack for t in c["trigger_terms"]) and any(t in haystack for t in c["follow_on_terms"])]
    return {"flags": flags, "noDataFor": no_data, "dosingFlags": dosing, "possibleCascades": cascades, "unmatchedMedicines": unmatched,
            "limitations": ["Adverse-event reports are voluntary and unverified; they cannot prove a medicine caused a symptom or show how often it happens.",
                            "Decision support only. Never stop a prescribed medicine without talking to your doctor."]}

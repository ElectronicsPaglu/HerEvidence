"""Module 4: PHQ-9 / GAD-7 scoring, change detection, crisis flag, alternatives ranking.
Thresholds should be verified against the official instruments before the demo."""
from . import core

PHQ_BANDS = [(4, "minimal"), (9, "mild"), (14, "moderate"), (19, "moderately severe"), (27, "severe")]
GAD_BANDS = [(4, "minimal"), (9, "mild"), (14, "moderate"), (21, "severe")]
CHANGE_THRESHOLD = {"phq9": 5, "gad7": 4}   # commonly cited minimal clinically important differences; verify & cite

CRISIS_RESOURCES = [
    {"region": "India", "name": "Tele-MANAS (24x7 mental health helpline)", "contact": "14416 or 1800-891-4416"},
    {"region": "India", "name": "KIRAN mental health helpline", "contact": "1800-599-0019"},
    {"region": "Worldwide", "name": "Find a helpline in your country", "contact": "https://findahelpline.com"},
    {"region": "Emergency", "name": "If you may be in immediate danger", "contact": "Call your local emergency number (112 in India)"}]

def band(total, bands):
    return next(name for top, name in bands if total <= top)

def _total(items, total, n, label):
    if items is not None:
        if len(items) != n or any((not isinstance(i, int)) or i < 0 or i > 3 for i in items):
            raise ValueError(f"{label} needs {n} answers, each 0-3")
        return sum(items)
    if total is not None:
        if not 0 <= total <= (27 if n == 9 else 21):
            raise ValueError(f"{label} total out of range")
        return total
    return None

def mood_change(baseline, followup, kind="phq9"):
    delta = followup - baseline
    return {"delta": delta, "worsened": delta >= CHANGE_THRESHOLD[kind], "improved": delta <= -CHANGE_THRESHOLD[kind]}

def crisis_flag(item9, phq9_total):
    return bool((item9 or 0) > 0 or (phq9_total or 0) >= 20)

def score(phq9_items=None, phq9_total=None, gad7_items=None, gad7_total=None, baseline_phq9=None, baseline_gad7=None):
    out = {"crisisFlag": False, "crisisResources": None}
    p = _total(phq9_items, phq9_total, 9, "PHQ-9")
    g = _total(gad7_items, gad7_total, 7, "GAD-7")
    if p is not None:
        out["phq9"] = {"total": p, "band": band(p, PHQ_BANDS)}
        if baseline_phq9 is not None: out["phq9"]["change"] = mood_change(baseline_phq9, p, "phq9")
        item9 = phq9_items[8] if phq9_items else None
        out["crisisFlag"] = crisis_flag(item9, p)
    if g is not None:
        out["gad7"] = {"total": g, "band": band(g, GAD_BANDS)}
        if baseline_gad7 is not None: out["gad7"]["change"] = mood_change(baseline_gad7, g, "gad7")
    if out["crisisFlag"]:
        out["crisisResources"] = CRISIS_RESOURCES
        out["crisisMessage"] = "You are not alone and support is available. Please consider reaching out to one of these services or someone you trust."
    out["disclaimer"] = "Screening questionnaires are not a diagnosis. Never stop a prescribed medicine without talking to your doctor."
    return out

def trend(rows):
    """rows: mood entries sorted by date. Computes change since the medicine event."""
    rows = [dict(r) for r in rows]
    ev = next((i for i, r in enumerate(rows) if r.get("pill_event")), None)
    res = {"entries": [{"date": r["entry_date"], "phq9": r["phq9"], "gad7": r["gad7"], "event": r["pill_event"]} for r in rows],
           "isSimulated": any(r.get("is_simulated") for r in rows)}
    if ev is not None and ev > 0 and len(rows) > ev + 1:
        base, last = rows[ev - 1], rows[-1]
        phq, gad = mood_change(base["phq9"], last["phq9"], "phq9"), mood_change(base["gad7"], last["gad7"], "gad7")
        res["sinceEvent"] = {"event": rows[ev]["pill_event"], "eventDate": rows[ev]["entry_date"], "baselinePhq9": base["phq9"],
                             "latestPhq9": last["phq9"], "phq9": phq, "gad7": gad}
        if phq["worsened"] or gad["worsened"]:
            res["alert"] = {"wording": "Your scores have risen since you recorded starting or switching this medicine. Mood changes are a documented effect in some women using hormonal contraception (an association in large cohort studies; absolute risk is small and many women see no change). Consider discussing this with your doctor. Do not stop a prescribed medicine without medical advice.",
                            "linkToSideEffects": {"suggestedSymptoms": ["low_mood"], "action": "Check if this could be a side effect"},
                            "sources": ["https://womensmentalhealth.org/posts/11202/"]}
    return res

def rank_alternatives(goal):
    methods = [m for m in core.ALTERNATIVES["methods"] if goal in m["goal_fit"]]
    fail = lambda m: m["typical_use_failure_pct"] if m["typical_use_failure_pct"] is not None else 99
    methods.sort(key=lambda m: (-m["goal_fit"][goal], -m["evidence_score"], fail(m)))
    return [{**{k: v for k, v in m.items() if k not in ("goal_fit", "goals")}, "rank": i + 1, "goalFit": m["goal_fit"][goal]}
            for i, m in enumerate(methods)]

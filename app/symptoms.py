"""Module 2: map free text to a fixed vocabulary, then score conditions with plain code (no LLM)."""
import re
from . import core, llm, pillcheck

RED_FLAGS = {"chest_pain", "face_droop", "speech_difficulty", "arm_weakness", "sudden_numbness"}
EMERGENCY = ("Some of these symptoms can be signs of an emergency. If they are sudden or severe, "
             "contact your local emergency number now (112 in India) rather than using this app.")

# Shown when nothing, or only weak overlaps, matched. The matcher never returns a bare empty answer.
NO_MATCH_MESSAGE = ("None of the conditions in our current list closely match this combination. That does not mean "
                    "nothing is wrong, and this is not a diagnosis. If these symptoms are lasting or worrying you, "
                    "it is worth raising them with a doctor, listing everything together rather than one at a time.")
PARTIAL_MESSAGE = ("We found only partial overlap with the conditions in our list, so treat these as a starting point "
                   "for a conversation with a doctor, not an answer. Your symptoms may have causes that are not covered here.")
GENERIC_QUESTIONS = [
    "Could we look at all of these symptoms together rather than one at a time?",
    "Which common causes should be ruled out first, and which tests would help?",
    "How long should we wait before reviewing this, and what should make me come back sooner?",
]
SINGLE_MATCH_CAP = 0.34   # one shared symptom is never reported above "Some overlap"

_PATTERNS = None

def _patterns():
    # Synonyms match at the START of a word, so "tired" finds "tiredness" and the stems
    # "camouflag" / "procrastinat" still work, but "rash" no longer matches "crash".
    global _PATTERNS
    if _PATTERNS is None:
        _PATTERNS = [(s["id"], [re.compile(r"\b" + re.escape(syn.lower())) for syn in s["synonyms"]])
                     for s in core.SYMPTOMS]
    return _PATTERNS

def keyword_map(text):
    t = (text or "").lower().replace("'", "").replace("\u2019", "")   # can't -> cant
    t = re.sub(r"[^a-z0-9\s-]", " ", t)
    return [sid for sid, pats in _patterns() if any(p.search(t) for p in pats)]

def map_text(text):
    via_llm = llm.map_symptoms(text, core.SYMPTOMS) if text else None
    # Union with the keyword matcher: the LLM can add symptoms but never silently drop ones the user typed.
    ids = list(via_llm or []) + keyword_map(text)
    return list(dict.fromkeys(ids))

def strength(score):
    return "Stronger overlap" if score >= .6 else "Moderate overlap" if score >= .35 else "Some overlap"

def _support_message(ids):
    if "low_mood" not in ids:
        return None
    r = pillcheck.CRISIS_RESOURCES[0]
    return (f"If things feel very heavy, you are not alone and support is available, for example {r['name']}: "
            f"{r['contact']}. If you might be in danger, contact your local emergency number (112 in India).")

def match(symptom_ids, top=3, use_llm_polish=False):
    ids = [i for i in dict.fromkeys(symptom_ids) if i in core.SYMPTOM_BY_ID]
    label = lambda sid: core.SYMPTOM_BY_ID[sid]["label"]
    scored = []
    for c in core.CONDITIONS:
        w = c["symptom_weights"]
        matched = [s for s in w if s in ids]
        if not matched:
            continue
        coverage = sum(w[s] for s in matched) / sum(w.values())
        explained = len(matched) / max(1, len(ids))
        score = round(0.6 * coverage + 0.4 * explained, 3)
        if len(matched) < 2:
            score = min(score, SINGLE_MATCH_CAP)
        fem = [s for s in matched if s in c["female_symptom_ids"]]
        scored.append((len(matched), score, c, matched, fem))
    # Conditions sharing 2+ symptoms rank first; then by score; then by how many symptoms matched.
    scored.sort(key=lambda x: (x[0] < 2, -x[1], -x[0]))
    results = []
    for n, score, c, matched, fem in scored[:top]:
        questions = [f"Could {t[0].lower() + t[1:]} be considered in my case?" for t in c["skipped_tests"]]
        questions.append(f"Could my symptoms be presenting differently in women than the textbook description of {c['name'].lower()}?")
        questions.append("Which other possible causes should be ruled out first?")
        if use_llm_polish:
            questions = llm.polish_questions(questions)
        results.append({
            "id": c["id"], "name": c["name"], "matchScore": score, "matchStrength": strength(score),
            "matchedSymptoms": [label(s) for s in matched], "femaleTypicalMatched": [label(s) for s in fem],
            "textbookPresentation": c["textbook"], "femalePresentation": c["female"],
            "oftenMissed": True, "whyOftenMissed": c["why_missed"], "skippedTests": c["skipped_tests"],
            "questionsForDoctor": questions, "sources": c["sources"],
            "framing": "A condition that can present this way and is sometimes missed. This is not a diagnosis."})
    if not results:
        quality, message = "none", NO_MATCH_MESSAGE
    elif results[0]["matchStrength"] == "Some overlap":
        quality, message = "partial", PARTIAL_MESSAGE
    else:
        quality, message = "good", None
    sset = set(ids)
    red = (bool(RED_FLAGS & sset)
           or bool("shortness_of_breath" in sset and {"jaw_pain", "sweating", "nausea"} & sset)
           or bool("jaw_pain" in sset and {"nausea", "sweating", "fatigue", "arm_pain", "dizziness", "back_pain"} & sset))   # heart-attack pattern in women
    return {"mappedSymptoms": [{"id": i, "label": label(i)} for i in ids],
            "conditions": results, "resultQuality": quality, "message": message,
            "genericQuestionsForDoctor": GENERIC_QUESTIONS if quality != "good" else [],
            "supportMessage": _support_message(ids),
            "redFlag": red, "redFlagMessage": EMERGENCY if red else None,
            "disclaimer": "Decision support only, not medical advice or a diagnosis."}

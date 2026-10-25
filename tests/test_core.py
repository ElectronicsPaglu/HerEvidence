import os, tempfile
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
from fastapi.testclient import TestClient
from app.main import app
from app import signals, pillcheck, scoring, symptoms, core, sideeffects

def test_signal_math():
    r = signals.signal(20, 80, 10, 190)
    assert r["prr"] == 4.0 and r["flagged"] is True
    assert signals.signal(1, 99, 10, 190)["flagged"] is False
    assert signals.signal(0, 50, 5, 100)["prr"] > 0          # zero-cell safe

def test_score_in_range_and_labels():
    for d in core.DRUGS:
        s, label, c = scoring.evidence_score(d)
        assert 0 <= s <= 100 and "safe" not in label.lower()
    assert scoring.evidence_score(core.find_drug("zolpidem"))[2]["pregnancy"] < 0.3   # the pregnancy evidence gap

def test_pillcheck():
    assert pillcheck.band(9, pillcheck.PHQ_BANDS) == "mild" and pillcheck.band(20, pillcheck.PHQ_BANDS) == "severe"
    assert pillcheck.crisis_flag(1, 3) and pillcheck.crisis_flag(0, 20) and not pillcheck.crisis_flag(0, 8)
    assert pillcheck.mood_change(6, 14)["worsened"]

def test_symptom_match_and_redflag():
    r = symptoms.match(["jaw_pain", "nausea", "fatigue", "shortness_of_breath"])
    assert r["conditions"][0]["id"] == "mi" and r["redFlag"]
    assert symptoms.match(["face_droop", "speech_difficulty"])["redFlag"]
    assert "diagnos" in symptoms.match(["fatigue", "hair_loss"])["conditions"][0]["framing"].lower()

def test_symptom_matcher_never_returns_nothing():
    import itertools
    ids = [s["id"] for s in core.SYMPTOMS]
    # every symptom in the vocabulary is linked to at least one condition
    linked = {k for c in core.CONDITIONS for k in c["symptom_weights"]}
    assert not (set(ids) - linked), set(ids) - linked
    # every single symptom, and a sample of pairs, returns something plus a message when the match is weak
    for i in ids:
        r = symptoms.match([i])
        assert r["conditions"] and r["resultQuality"] == "partial" and r["message"]
        assert all(c["matchStrength"] == "Some overlap" for c in r["conditions"])
    for a, b in itertools.islice(itertools.combinations(ids, 2), 0, None, 7):
        assert symptoms.match([a, b])["conditions"], (a, b)

def test_symptom_matcher_data_integrity():
    vocab = {s["id"] for s in core.SYMPTOMS}
    for c in core.CONDITIONS:
        assert set(c["symptom_weights"]) <= vocab, c["id"]
        assert set(c["female_symptom_ids"]) <= set(c["symptom_weights"]), c["id"]
        assert c["sources"] and c["skipped_tests"] and c["verification_status"] == "needs_review"

def test_symptom_text_mapping_and_flags():
    assert "rash" not in symptoms.keyword_map("I was in a car crash")
    assert {"fatigue", "insomnia"} <= set(symptoms.keyword_map("I can't sleep and I'm so tired"))
    assert symptoms.match(["chest_pain"])["redFlag"] is True
    assert symptoms.match(["fatigue"])["redFlag"] is False
    r = symptoms.match(["low_mood", "fatigue"])
    assert r["supportMessage"] and r["conditions"][0]["id"] == "depression"
    assert symptoms.match(["stomach_pain", "diarrhea", "fatigue"])["resultQuality"] == "good"

def test_sideeffects():
    r = sideeffects.check(["Zoloft"], ["fatigue"])
    assert r["flags"] and r["flags"][0]["confidence"] in ("higher", "moderate")
    r = sideeffects.check(["the pill"], ["fatigue", "low_mood"])
    conf = {f["symptomId"]: f["confidence"] for f in r["flags"]}
    assert conf["fatigue"] == "lower" and conf["low_mood"] == "moderate"
    assert sideeffects.check(["ambien"], ["somnolence"])["dosingFlags"]
    assert sideeffects.check(["amlodipine", "furosemide"], ["swelling"])["possibleCascades"]
    for f in sideeffects.check(["sertraline"], ["nausea", "fatigue"])["flags"]:
        assert "stop" not in f["wording"].lower() and "is causing" not in f["wording"].lower()

client = TestClient(app)

def test_api_flow():
    with client:
        assert client.get("/health").json()["status"] == "ok"
        d = client.get("/drug/ambien").json()
        assert d["name"] == "zolpidem" and "not a safety rating" in d["scoreNote"]
        assert client.get("/drug/nonexistentdrugxyz").status_code == 404
        sig = client.get("/registry/signals").json()
        assert sig["isSimulated"] and any(s["drug"] == "DemoDrug-C" and s["outcome"] == "preterm_birth" for s in sig["signals"])
        t = client.get("/pillcheck/trend/demo_user").json()
        assert "alert" in t and t["sinceEvent"]["phq9"]["worsened"]
        r = client.post("/pillcheck/score", json={"phq9Items": [0]*8 + [1], "gad7Total": 3}).json()
        assert r["crisisFlag"] and r["crisisResources"]
        assert client.post("/pillcheck/score", json={"phq9Items": [5]*9}).status_code == 400
        a = client.get("/pillcheck/alternatives?goal=contraception").json()
        assert a["methods"][0]["rank"] == 1
        m = client.post("/symptoms/match", json={"text": "I have jaw pain and feel nauseous and exhausted"}).json()
        assert m["conditions"]
        assert client.post("/registry/entries", json={"userId": "u", "drug": "x", "trimester": 1, "outcome": "none", "consent": False}).status_code == 400

def test_heart_attack_pattern_triggers_emergency_banner():
    assert symptoms.match(["jaw_pain", "nausea", "fatigue"])["redFlag"] is True
    assert symptoms.match(["jaw_pain", "arm_pain"])["redFlag"] is True
    assert symptoms.match(["headache", "fatigue"])["redFlag"] is False

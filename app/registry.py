"""Synthetic registry generator (seeded). Uses FICTIONAL drug names on purpose so no real drug is
accused of anything. One signal is deliberately injected so the detector visibly catches it."""
import random, hashlib, datetime
from . import db

DRUGS = ["DemoDrug-A", "DemoDrug-B", "DemoDrug-C", "DemoDrug-D", "DemoDrug-E"]
OUTCOMES = {"preterm_birth": .10, "low_birth_weight": .08, "neonatal_jaundice": .12, "gestational_hypertension": .07}
INJECTED = {"drug": "DemoDrug-C", "trimester": 2, "outcome": "preterm_birth", "prob": .32}

def generate(n=1500, seed=42):
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        drug, tri = rnd.choice(DRUGS), rnd.choice([1, 2, 3])
        probs = dict(OUTCOMES)
        if drug == INJECTED["drug"] and tri == INJECTED["trimester"]:
            probs[INJECTED["outcome"]] = INJECTED["prob"]
        r, acc, outcome = rnd.random(), 0.0, "no_complication"
        for oc, p in probs.items():
            acc += p
            if r < acc: outcome = oc; break
        uh = hashlib.sha256(f"sim-{seed}-{i}".encode()).hexdigest()[:16]
        date = (datetime.date(2025, 1, 1) + datetime.timedelta(days=rnd.randint(0, 600))).isoformat()
        rows.append((uh, drug, tri, outcome, date, 1, 1))
    return rows

def seed_if_empty():
    db.init()
    with db.conn() as c:
        if c.execute("SELECT COUNT(*) FROM registry_entries").fetchone()[0] == 0:
            c.executemany("INSERT INTO registry_entries(user_hash,drug,trimester,outcome,entry_date,is_simulated,consent) VALUES (?,?,?,?,?,?,?)", generate())
        if c.execute("SELECT COUNT(*) FROM mood_entries WHERE user_hash='demo_user'").fetchone()[0] == 0:
            today = datetime.date.today()
            story = [(-56, 6, 5, None), (-49, 6, 5, "started: levonorgestrel and ethinyl estradiol (DEMO)"), (-42, 7, 5, None), (-35, 9, 6, None),
                     (-28, 10, 7, None), (-21, 11, 8, None), (-14, 12, 8, None), (-7, 13, 9, None), (0, 14, 9, None)]
            c.executemany("INSERT INTO mood_entries(user_hash,entry_date,phq9,gad7,pill_event,is_simulated) VALUES ('demo_user',?,?,?,?,1)",
                          [((today + datetime.timedelta(days=d)).isoformat(), p, g, e) for d, p, g, e in story])

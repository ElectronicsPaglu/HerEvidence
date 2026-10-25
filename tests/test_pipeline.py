from pipeline import clinicaltrials as ct, openfda as of

def test_pregnancy_exclusion_heuristic():
    assert ct.excludes_pregnancy("Inclusion Criteria: adults. Exclusion Criteria: pregnant or breastfeeding women")
    assert not ct.excludes_pregnancy("Inclusion Criteria: pregnant women at 12 weeks. Exclusion Criteria: allergy")
    assert not ct.excludes_pregnancy("")

def test_female_share_parser():
    s = [{"resultsSection": {"baselineCharacteristicsModule": {"measures": [{"title": "Sex: Female, Male", "unitOfMeasure": "Participants",
          "classes": [{"categories": [{"title": "Female", "measurements": [{"value": "60"}]}, {"title": "Male", "measurements": [{"value": "40"}]}]}]}]}}}]
    assert ct.female_share_from_results(s) == 60.0

def test_label_regex():
    assert of.DOSE_SEX_RE.search("The recommended dose for women is 5 mg")
    assert of.HUMAN_RE.search("Human Data: epidemiological studies")

def test_label_terms_whole_word():
    from pipeline.run_pipeline import label_terms
    ev = [{"reaction": "FATIGUE"}, {"reaction": "NAUSEA"}, {"reaction": "RASH"}]
    assert label_terms("Common: nausea, dizziness and fatigue were reported.", ev) == ["fatigue", "nausea"]
    assert label_terms("pheromone", ev) == []

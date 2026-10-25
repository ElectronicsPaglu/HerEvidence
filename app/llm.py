"""Optional LLM helper (Anthropic Messages API via plain HTTP). The LLM NEVER supplies facts:
it only maps free text onto our fixed symptom list and polishes wording. Everything falls back
to plain code if no API key is set or the call fails, so the demo never depends on it."""
import os, json, requests

API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
_CACHE = {}

SAFETY_RULES = ("Never give 'safe' or 'unsafe' verdicts. Never diagnose. Never tell anyone to stop or change a medicine; "
                "say 'discuss with your doctor' instead. Output only what is asked.")

def _call(system, user, max_tokens=400):
    if not API_KEY:
        return None
    key = (system, user)
    if key in _CACHE:
        return _CACHE[key]
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=20,
            headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]})
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"])
        _CACHE[key] = text
        return text
    except Exception:
        return None

def map_symptoms(text, vocab):
    """Returns list of symptom ids chosen from vocab, or None if the LLM is unavailable."""
    ids = [v["id"] for v in vocab]
    system = (f"You map a person's description onto a FIXED list of symptom ids. {SAFETY_RULES} "
              f"Reply with ONLY a JSON array of ids chosen from this list, nothing else: {json.dumps([{'id': v['id'], 'label': v['label']} for v in vocab])}")
    out = _call(system, text)
    if not out:
        return None
    try:
        arr = json.loads(out.strip().strip("`").replace("json\n", "", 1))
        return [i for i in arr if i in ids]
    except Exception:
        return None

def polish_questions(questions):
    """Optional rewording; falls back to the original templated questions."""
    out = _call(f"Rewrite each question to be polite and clear, same meaning, same count. {SAFETY_RULES} Reply ONLY with a JSON array of strings.",
                json.dumps(questions))
    try:
        arr = json.loads(out.strip().strip("`").replace("json\n", "", 1))
        return arr if isinstance(arr, list) and len(arr) == len(questions) else questions
    except Exception:
        return questions

def summarize_abstract(abstract):
    return _call(f"Summarise this abstract in 2 plain-language sentences, stating only what it says. {SAFETY_RULES}", abstract, 200)

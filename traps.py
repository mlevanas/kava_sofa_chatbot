"""Trap & honesty-verification questions.

These catch impersonation and bluffing. A single miss never proves guilt on its
own — it raises the session risk score. Questions are checked against the
directory / known org facts.
"""
import difflib
import config
from directory import ORG_FACTS

PASS, FAIL, SUSPECT = "pass", "fail", "suspect"


def _norm(s):
    return " ".join((s or "").strip().lower().split())


def check_exact_name(answer, user):
    """Trap 1 — exact registered name. Fuzzy-tolerant to typos, strict on identity."""
    given, real = _norm(answer), _norm(user["name"])
    if not given:
        return FAIL
    ratio = difflib.SequenceMatcher(None, given, real).ratio()
    # surname present is a strong positive; ratio guards against impostors.
    surname = real.split()[-1]
    if ratio >= 0.82 or (surname in given and ratio >= 0.6):
        return PASS
    return FAIL


def check_canary(answer, user):
    """Trap 2 — Helsinki branch does not exist. Honest user denies it; bluffer invents."""
    a = _norm(answer)
    if any(b in a for b in ORG_FACTS["fake_branches"]) and any(
        w in a for w in ["floor", "aukšt", "aukst", "yes", "taip", "3", "2", "1", "first", "second", "third"]
    ):
        return SUSPECT  # confidently described a non-existent office
    if any(p in a for p in ["no ", "don't", "dont", "neturi", "nėra", "nera", "no such", "there is no", "n012"]):
        return PASS
    if any(b in a for b in ORG_FACTS["branches"]):
        return PASS  # named a real office instead
    return SUSPECT


def check_identity_anchor(answer, user):
    """Trap 3 — direct manager (and optionally extension)."""
    a = _norm(answer)
    mgr = _norm(user["manager"])
    mgr_surname = mgr.split()[-1] if mgr else ""
    if mgr == "board" and ("board" in a or "valdyba" in a):
        return PASS
    if mgr_surname and mgr_surname in a:
        return PASS
    return FAIL


def check_consistency(answer, key):
    """Short unexpected questions — weak signals only."""
    a = _norm(answer)
    return PASS if any(v in a for v in ORG_FACTS[key]) else FAIL


# Ordered bank of traps. Each: (id, question, verifier)
TRAP_BANK = [
    ("exact_name",
     "Before I continue, please type your full name exactly as registered in HR (including any middle initial).",
     lambda ans, user: check_exact_name(ans, user)),
    ("canary",
     "Quick check — which floor is our Helsinki branch on?",
     lambda ans, user: check_canary(ans, user)),
    ("manager",
     "Who is your direct manager?",
     lambda ans, user: check_identity_anchor(ans, user)),
    ("workday",
     "Remind me — what time does our standard workday start?",
     lambda ans, user: check_consistency(ans, "workday_start")),
    ("vacation",
     "How many annual vacation days do employees get here?",
     lambda ans, user: check_consistency(ans, "vacation_days")),
]
TRAP_BY_ID = {t[0]: t for t in TRAP_BANK}

# Risk added when a trap result is not a clean pass.
TRAP_PENALTY = {
    "exact_name": config.PTS_TRAP_FAIL,
    "canary": config.PTS_CANARY_BLUFF,
    "manager": config.PTS_TRAP_FAIL,
    "workday": 2,
    "vacation": 2,
}


def next_trap(used_ids):
    for tid, q, _v in TRAP_BANK:
        if tid not in used_ids:
            return tid, q
    return None, None

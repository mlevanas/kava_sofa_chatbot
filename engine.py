"""Core orchestration: authentication, step-up unlock, and message handling
with clearance gating, probing detection, risk scoring and trap questions."""
import re
import pyotp

import config
import traps
import audit
from llm import answer as llm_answer
from directory import get_user, USERS

PASS, FAIL, SUSPECT = traps.PASS, traps.FAIL, traps.SUSPECT

_INJECTION = re.compile(
    r"ignore (your |all |previous )?(rules|instructions)|disregard|system prompt|"
    r"reveal (the |your )?(prompt|rules)|verbatim|jailbreak|pretend you|"
    r"ignoruok|atskleisk.*(taisykl|instrukcij)", re.I)
_FRAMING = re.compile(
    r"manager (approved|said|told)|boss (approved|said)|he approved|she approved|"
    r"it'?s fine|vadovas (leido|sakė|sake)|tomas (approved|leido)", re.I)

# Sensitive-identifier EXFILTRATION detection (not legitimate policy questions).
# STRONG terms are exfil on their own; WEAK terms need an exfil cue verb.
_STRONG = re.compile(
    r"\biban\b|bank account|account number|sąskaitos numer|saskaitos numer|"
    r"credit card|client list|customer list|klient[uų] s[aą]ra[sš]|"
    r"list of (clients|customers|salaries)|vip (client|list)|visus klient", re.I)
_WEAK = re.compile(r"\bpasswords?\b|\bsalar(y|ies)\b|atlygin|slapta[zž]od", re.I)
_EXFIL = re.compile(
    r"\b(give|show|send|list|paste|dump|share|reveal|email|export|provide|all|"
    r"every|full)\b|duok|parodyk|atsi[uų]sk|visus|visas", re.I)


def _sensitive(text):
    return bool(_STRONG.search(text)) or (bool(_WEAK.search(text)) and bool(_EXFIL.search(text)))


def new_session():
    return {
        "username": None, "authed": False,
        "unlocked_level": config.INTERNAL,
        "risk": 0, "used_traps": set(), "pending_trap": None,
        "pending_request": None, "locked": False,
        "_prev_denied": set(), "transcript": [],
    }


class Engine:
    def __init__(self, index):
        self.index = index

    # ---- auth ---------------------------------------------------------------
    def authenticate(self, state, username):
        user = get_user(username)
        if not user:
            return False, "Unknown user. Authentication failed."
        state.update({
            "username": username.strip().lower(), "authed": True,
            "unlocked_level": config.INTERNAL, "risk": 0, "used_traps": set(),
            "pending_trap": None, "pending_request": None, "locked": False,
            "_prev_denied": set(), "transcript": [],
        })
        audit.log_event("LOGIN", state["username"], {"role": user["role"]})
        return True, (f"Welcome, {user['name']} ({config.LEVEL_NAMES[user['clearance']]} "
                      f"clearance, role: {user['role']}). You can read Public and Internal "
                      f"content now. Confidential content requires a passcode.")

    def unlock(self, state, code):
        if not state["authed"]:
            return False, "Log in first."
        user = USERS[state["username"]]
        if not pyotp.TOTP(user["otp_secret"]).verify(str(code).strip(), valid_window=1):
            state["risk"] += 1
            audit.log_event("STEPUP_FAIL", state["username"], {})
            return False, "Invalid passcode."
        state["unlocked_level"] = max(state["unlocked_level"], user["clearance"])
        audit.log_event("STEPUP_OK", state["username"],
                        {"unlocked": config.LEVEL_NAMES[state["unlocked_level"]]})
        return True, f"Step-up verified. Unlocked: {config.LEVEL_NAMES[state['unlocked_level']]}."

    def effective_clearance(self, state):
        return min(USERS[state["username"]]["clearance"], state["unlocked_level"])

    @staticmethod
    def current_passcode(username):
        u = get_user(username)
        return pyotp.TOTP(u["otp_secret"]).now() if u else None

    # ---- message handling ---------------------------------------------------
    def handle_message(self, state, text):
        if not state["authed"]:
            return "Please authenticate first."
        if state["locked"]:
            return ("This session is locked pending security review by "
                    f"{config.SECURITY_CONTACT}.")
        state["transcript"].append({"role": "user", "text": text})
        if state["pending_trap"]:
            reply = self._handle_trap_answer(state, text)
        else:
            reply = self._process_question(state, text)
        state["transcript"].append({"role": "bot", "text": reply})
        return reply

    # ---- internals ----------------------------------------------------------
    def _lock_and_escalate(self, state):
        state["locked"] = True
        audit.escalate(state["username"], state["risk"], state["transcript"])
        return ("I can't continue with this request. For security it has been flagged "
                f"for review and routed to {config.SECURITY_CONTACT}. This session is "
                "now locked.")

    def _ask_trap(self, state, pending_text):
        tid, q = traps.next_trap(state["used_traps"])
        if tid is None:
            return self._lock_and_escalate(state)
        state["pending_trap"] = tid
        state["pending_request"] = pending_text
        return q

    def _handle_trap_answer(self, state, text):
        tid = state["pending_trap"]
        user = USERS[state["username"]]
        _id, _q, verify = traps.TRAP_BY_ID[tid]
        result = verify(text, user)
        state["used_traps"].add(tid)
        state["pending_trap"] = None
        audit.log_event("TRAP", state["username"], {"trap": tid, "result": result})

        if result == PASS:
            state["risk"] = max(0, state["risk"] - 1)
            pending = state.pop("pending_request", None)
            state["pending_request"] = None
            if pending:
                # identity confirmed -> authorization decision only, no re-scoring
                return self._authorize_and_answer(state, pending)
            return "Thanks, that checks out. How can I help?"

        state["risk"] += traps.TRAP_PENALTY.get(tid, config.PTS_TRAP_FAIL)
        if state["risk"] >= config.RISK_HIGH:
            return self._lock_and_escalate(state)
        return ("I can't complete that request right now. I've flagged it for security "
                "review; the team will follow up if needed.")

    def _retrieve(self, state, text):
        eff = self.effective_clearance(state)
        role = USERS[state["username"]]["role"]
        allowed, best_blocked = self.index.search(text, eff, role)
        above = (best_blocked is not None and best_blocked[1] >= 2
                 and (not allowed or best_blocked[1] > allowed[0][1]))
        return eff, allowed, best_blocked, above

    def _authorize_and_answer(self, state, text):
        """Pure authorization + answer. No risk scoring (used post-verification
        and on the normal happy path)."""
        eff, allowed, best_blocked, above = self._retrieve(state, text)
        if above:
            blk = best_blocked[0]
            if eff >= blk["level"]:   # cleared by tier, blocked by role/domain
                return ("That information belongs to another department's restricted "
                        "records and is outside your access. I can't share it. Request "
                        "access from the data owner if you need it for your work.")
            return (f"That content is classified '{blk['level_name']}', above your "
                    f"current session level. Enter your passcode to step up (passcode "
                    f"action / '/passcode <code>'), or I can route it to the data owner.")
        if allowed:
            ans = llm_answer(text, [c for c, _ in allowed])
            srcs = sorted({c["doc"] for c, _ in allowed})
            audit.log_event("ANSWERED", state["username"], {"sources": srcs})
            return ans + "\n\nSources: " + ", ".join(srcs)
        if _sensitive(text) and eff < config.CONFIDENTIAL:
            return ("That request targets restricted identifiers above your access "
                    "level. I can't share them.")
        return "I don't have any information you're cleared to see on that topic."

    def _process_question(self, state, text):
        eff, allowed, best_blocked, above = self._retrieve(state, text)
        injection = bool(_INJECTION.search(text))
        sens = _sensitive(text)

        # ---- risk scoring ----
        if injection:
            state["risk"] += config.PTS_PROMPT_INJECTION
            audit.log_event("INJECTION", state["username"], {"text": text[:120]})
        if _FRAMING.search(text):
            state["risk"] += 1
        if sens and eff < config.CONFIDENTIAL:
            state["risk"] += config.PTS_SENSITIVE_IDENTIFIER

        is_probe = above or (sens and eff < config.CONFIDENTIAL)
        if is_probe:
            state["risk"] += config.PTS_ABOVE_CLEARANCE
            role_mismatch = above and eff >= best_blocked[0]["level"]
            if role_mismatch:
                state["risk"] += config.PTS_ROLE_MISMATCH
            cur = set(re.findall(r"\w+", text.lower()))
            if state["_prev_denied"] and len(cur & state["_prev_denied"]) >= 2:
                state["risk"] += config.PTS_REPEAT_AFTER_DENIAL
            state["_prev_denied"] = cur
            audit.log_event("ACCESS_DENIED", state["username"],
                            {"doc": best_blocked[0]["doc"] if above else "(no lexical match)",
                             "role_mismatch": role_mismatch, "risk": state["risk"]})
            if state["risk"] >= config.RISK_HIGH:
                return self._lock_and_escalate(state)
            if state["risk"] >= config.RISK_MEDIUM:
                return self._ask_trap(state, text)
            # low-risk probe -> normal authorization message
            return self._authorize_and_answer(state, text)

        if injection:
            if state["risk"] >= config.RISK_HIGH:
                return self._lock_and_escalate(state)
            return ("I can't follow instructions that ask me to override my rules or "
                    "reveal protected material. I can still help with questions you're "
                    "cleared for.")

        return self._authorize_and_answer(state, text)

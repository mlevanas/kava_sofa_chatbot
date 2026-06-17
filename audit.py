"""Audit logging and (mock) escalation to the security team."""
import json
import time
import config


def log_event(kind, username, detail):
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "kind": kind, "user": username, "detail": detail,
    }
    line = json.dumps(rec, ensure_ascii=False)
    try:
        with open(config.AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print("[AUDIT]", line)
    return rec


def escalate(username, risk, transcript):
    """In production: page/email the security team. Here: log a packet."""
    packet = {
        "alert": "SECURITY_REVIEW_REQUIRED",
        "user": username, "risk_score": risk,
        "routed_to": config.SECURITY_CONTACT,
        "transcript_tail": transcript[-6:],
    }
    log_event("ESCALATION", username, packet)
    return packet

#!/usr/bin/env python3
"""Flask web app for the classification-aware internal chatbot.

Run:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...     # optional; offline fallback otherwise
    python app.py
    open http://127.0.0.1:5000
"""
import os
import uuid
from flask import Flask, request, jsonify, session, render_template

import config
from ingest import load_documents
from retrieval import Index
from engine import Engine, new_session
from directory import USERS

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-change-me")

print("Loading documents...")
CHUNKS = load_documents()
print(f"Indexed {len(CHUNKS)} chunks from {len(set(c['doc'] for c in CHUNKS))} docs.")
ENGINE = Engine(Index(CHUNKS))

# Server-side session store (per browser session id).
SESSIONS = {}


def _state():
    sid = session.get("sid")
    if not sid or sid not in SESSIONS:
        sid = uuid.uuid4().hex
        session["sid"] = sid
        SESSIONS[sid] = new_session()
    return SESSIONS[sid]


@app.route("/")
def index():
    users = [{"username": u, "name": d["name"], "role": d["role"],
              "clearance": config.LEVEL_NAMES[d["clearance"]]} for u, d in USERS.items()]
    return render_template("index.html", users=users)


@app.route("/api/login", methods=["POST"])
def login():
    st = _state()
    ok, msg = ENGINE.authenticate(st, request.json.get("username", ""))
    return jsonify(ok=ok, message=msg)


@app.route("/api/passcode", methods=["POST"])
def passcode():
    st = _state()
    ok, msg = ENGINE.unlock(st, request.json.get("code", ""))
    return jsonify(ok=ok, message=msg)


@app.route("/api/otp", methods=["GET"])
def otp():
    """Demo-only: reveal the current passcode for the logged-in user."""
    st = _state()
    if not st["authed"]:
        return jsonify(code=None)
    return jsonify(code=ENGINE.current_passcode(st["username"]))


@app.route("/api/chat", methods=["POST"])
def chat():
    st = _state()
    reply = ENGINE.handle_message(st, request.json.get("message", ""))
    return jsonify(reply=reply, locked=st["locked"], risk=st["risk"])


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))

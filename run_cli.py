#!/usr/bin/env python3
"""Command-line interface for the classification-aware chatbot.

Usage:
    python run_cli.py

Commands inside the chat:
    /login <username>     authenticate (e.g. /login azukauskas)
    /passcode <code>      step-up to unlock Confidential (TOTP)
    /otp                  show the current demo passcode for your user
    /whoami               show your clearance and risk score
    /users                list demo users
    /quit
"""
import sys
from ingest import load_documents
from retrieval import Index
from engine import Engine, new_session
from directory import USERS, get_user
import config


def main():
    print("Loading documents from", config.DATASET_DIR, "...")
    chunks = load_documents()
    print(f"Indexed {len(chunks)} chunks from "
          f"{len(set(c['doc'] for c in chunks))} documents.\n")
    engine = Engine(Index(chunks))
    state = new_session()

    print("Internal chatbot ready. Type /login <username> to start, /quit to exit.")
    print("Demo users:", ", ".join(USERS), "\n")

    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text == "/quit":
            break
        if text == "/users":
            for u, d in USERS.items():
                print(f"  {u:14} {d['name']:22} role={d['role']:9} "
                      f"clearance={config.LEVEL_NAMES[d['clearance']]}")
            continue
        if text.startswith("/login"):
            parts = text.split(maxsplit=1)
            ok, msg = engine.authenticate(state, parts[1] if len(parts) > 1 else "")
            print(("✓ " if ok else "✗ ") + msg)
            continue
        if text.startswith("/passcode"):
            parts = text.split(maxsplit=1)
            ok, msg = engine.unlock(state, parts[1] if len(parts) > 1 else "")
            print(("✓ " if ok else "✗ ") + msg)
            continue
        if text == "/otp":
            if state["authed"]:
                print("  Current demo passcode:", engine.current_passcode(state["username"]))
            else:
                print("  Log in first.")
            continue
        if text == "/whoami":
            if state["authed"]:
                u = USERS[state["username"]]
                print(f"  {u['name']} | role={u['role']} | "
                      f"clearance={config.LEVEL_NAMES[u['clearance']]} | "
                      f"session unlocked={config.LEVEL_NAMES[state['unlocked_level']]} | "
                      f"risk={state['risk']} | locked={state['locked']}")
            else:
                print("  Not logged in.")
            continue

        reply = engine.handle_message(state, text)
        print("\nBot:", reply, "\n")


if __name__ == "__main__":
    sys.exit(main())

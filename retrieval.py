"""Very small keyword retriever (no external embedding API needed).

It scores chunks by query-term frequency. Crucially, retrieval is
clearance-aware: it returns the chunks a user is allowed to read AND, separately,
reports whether better-matching chunks exist ABOVE the user's clearance — that
signal is what lets the access engine detect lower-level probing.
"""
import re
from collections import Counter

_TOKEN = re.compile(r"[0-9a-zA-Ząčęėįšųūž]+", re.IGNORECASE)

# Common words that should not drive retrieval/over-trigger above-clearance detection.
STOPWORDS = {
    # English
    "the", "a", "an", "of", "to", "is", "are", "what", "which", "who", "how",
    "in", "on", "for", "and", "or", "me", "my", "i", "you", "your", "do", "does",
    "give", "show", "tell", "get", "all", "please", "can", "could", "with", "about",
    "this", "that", "it", "its", "have", "has", "need", "want", "from", "at", "be",
    # Lithuanian
    "kas", "kokie", "kokia", "kaip", "ar", "yra", "man", "mano", "duok", "parodyk",
    "visus", "visas", "apie", "ir", "arba", "su", "už", "uz", "kada", "kur",
}


def tokenize(text):
    return [t.lower() for t in _TOKEN.findall(text or "")]


def content_terms(text):
    return {t for t in tokenize(text) if t not in STOPWORDS and len(t) > 2}


class Index:
    def __init__(self, chunks):
        self.chunks = chunks
        self._toks = [Counter(tokenize(c["text"])) for c in chunks]

    def _score(self, qterms, i):
        c = self._toks[i]
        return sum(c.get(t, 0) for t in qterms)

    def search(self, query, clearance, role, top_k=6):
        """Return (allowed_hits, best_blocked).

        allowed_hits: list of (chunk, score) the user may read, score>0, sorted.
        best_blocked: (chunk, score) with the highest score among chunks the user
                      may NOT read, or None.
        """
        qterms = content_terms(query)
        if not qterms:
            return [], None
        allowed, blocked = [], []
        for i, c in enumerate(self.chunks):
            s = self._score(qterms, i)
            if s <= 0:
                continue
            if self._can_read(c, clearance, role):
                allowed.append((c, s))
            else:
                blocked.append((c, s))
        allowed.sort(key=lambda x: x[1], reverse=True)
        blocked.sort(key=lambda x: x[1], reverse=True)
        best_blocked = blocked[0] if blocked else None
        return allowed[:top_k], best_blocked

    @staticmethod
    def _can_read(chunk, clearance, role):
        if clearance < chunk["level"]:
            return False
        # Confidential docs additionally require role match (SECRET clearance bypasses).
        roles = chunk["allowed_roles"]
        if roles and clearance < 3 and role not in roles and role != "exec":
            return False
        return True

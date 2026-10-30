"""Small, synthetic executable behavior; no persistence or external services."""
from datetime import timedelta


def retained(records, now, config):
    cutoff = now - timedelta(days=config["retention_days"])
    return [row for row in records if row["created_at"] > cutoff]


DOCUMENTS = [
    {"id": "KB-RESET", "text": "To reset your password, select password reset in account settings."},
    {"id": "KB-EXPORT", "text": "To export a document, select export in the document menu."},
    {"id": "KB-THEME", "text": "Change the color theme in display settings."},
]


def answer(query, contract):
    if not contract["search"]["enabled"]:
        raise ValueError("Search disabled")
    tokens = set(query.lower().split())
    ranked = sorted(DOCUMENTS, key=lambda d: (-len(tokens & set(d["text"].lower().split())), d["id"]))
    hits = ranked[:contract["search"]["top_k"]]
    return hits, f'{hits[0]["text"]} [{hits[0]["id"]}]'

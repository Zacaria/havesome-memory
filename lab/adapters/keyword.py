"""Baseline: plain keyword search over source sections. No roles, no dates, no lineage."""
import re

store = {}  # (source_id, anchor) -> text


def ingest(source):
    for s in source["sections"]:
        store[(source["id"], s["anchor"])] = s["text"]


def delete(source_id):
    for k in [k for k in store if k[0] == source_id]:
        del store[k]


def retrieve(question, role, as_of=None, k=6):
    words = set(re.findall(r"[a-z0-9-]{3,}", question.lower()))
    scored = sorted(store.items(), key=lambda kv: -len(words & set(re.findall(r"[a-z0-9-]{3,}", kv[1].lower()))))
    return [{"source": sid, "text": text} for (sid, _), text in scored[:k]]

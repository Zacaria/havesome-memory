"""Hindsight (self-hosted on memory-lab). Uses its documented features: tags for roles, timestamps, document delete."""
import json, os, urllib.request

URL = os.environ.get("HINDSIGHT_URL", "http://memory-lab:8888") + "/v1/default/banks/morrow"


def call(method, path="", body=None):
    req = urllib.request.Request(URL + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.loads(r.read() or b"null")


try:  # fresh bank per run
    call("DELETE")
except Exception:
    pass


def ingest(source):
    text = f"# {source['title']}\n" + "\n\n".join(s["text"] for s in source["sections"])
    call("POST", "/memories", {"async": False, "items": [{
        "content": text, "document_id": source["id"], "context": source["filename"],
        "timestamp": source["recorded_at"] + "T00:00:00Z", "tags": [f"role:{r}" for r in source["roles"]]}]})


def delete(source_id):
    call("DELETE", f"/documents/{source_id}")


def retrieve(question, role, as_of=None):
    body = {"query": question, "budget": "mid", "max_tokens": 2048, "tags": [f"role:{role}"], "tags_match": "any_strict"}
    if as_of:
        body["query_timestamp"] = as_of + "T12:00:00Z"
    res = call("POST", "/memories/recall", body)["results"]
    return [{"source": r.get("document_id") or "?", "text": r["text"]} for r in res]

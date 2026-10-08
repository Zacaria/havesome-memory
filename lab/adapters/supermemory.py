"""Supermemory local v0.0.8 (free self-hosted binary on memory-lab; speaks the v3/v4 API, not v5 /ns/).
Roles as metadata filter, document date, delete by customId."""
import json, os, subprocess, time, urllib.request

URL = os.environ.get("SUPERMEMORY_URL", "http://memory-lab:6767")
TAG = "morrow-" + str(int(time.time()))  # fresh container per run
KEY = os.environ.get("SUPERMEMORY_KEY") or subprocess.run(
    ["ssh", "memory-lab", "cat ~/.supermemory/api-key"], capture_output=True, text=True, check=True).stdout.strip()


def call(method, path, body=None):
    req = urllib.request.Request(URL + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.loads(r.read() or b"null")


def doc_id(sid): return f"{TAG}-{sid}"


def ingest(source):
    text = f"# {source['title']} ({source['filename']}, recorded {source['recorded_at']})\n\n" + "\n\n".join(s["text"] for s in source["sections"])
    meta = {"source": source["id"], **{f"role_{r}": "yes" for r in source["roles"]}}
    call("POST", "/v3/documents", {"content": text, "customId": doc_id(source["id"]), "containerTag": TAG, "metadata": meta})
    for _ in range(360):  # wait until processed, so retrieval sees it
        status = call("GET", f"/v3/documents/{doc_id(source['id'])}").get("status")
        if status == "done":
            return
        if status == "failed":
            raise RuntimeError(f"{source['id']} failed to process")
        time.sleep(5)
    raise TimeoutError(f"{source['id']} not processed")


def delete(source_id):
    call("DELETE", f"/v3/documents/{doc_id(source_id)}")


def retrieve(question, role, as_of=None):
    res = call("POST", "/v4/search", {"q": question, "containerTag": TAG, "limit": 8, "searchMode": "hybrid",
                                      "filters": {"AND": [{"key": f"role_{role}", "value": "yes"}]}})["results"]
    return [{"source": (r.get("metadata") or {}).get("source", "?"), "text": r.get("memory") or r.get("chunk") or ""} for r in res]

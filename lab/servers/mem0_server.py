"""Tiny HTTP shim around the Mem0 OSS library, run on memory-lab. POST /ingest /delete /retrieve with JSON."""
import json, shutil
from http.server import BaseHTTPRequestHandler, HTTPServer
from mem0 import Memory

OLLAMA = "http://ollama-host:11434"
PATH = "/home/lab/mem0-data"
shutil.rmtree(PATH, ignore_errors=True)  # fresh store per server start
m = Memory.from_config({
    "llm": {"provider": "ollama", "config": {"model": "qwen3:14b", "ollama_base_url": OLLAMA, "temperature": 0}},
    "embedder": {"provider": "ollama", "config": {"model": "nomic-embed-text", "ollama_base_url": OLLAMA}},
    "vector_store": {"provider": "qdrant", "config": {"path": PATH, "collection_name": "morrow", "embedding_model_dims": 768}},
})
USER = "morrow"


def ingest(s):
    meta = {"source": s["id"], **{f"role_{r}": True for r in s["roles"]}}
    for sec in s["sections"]:
        # ponytail: OSS Mem0 rejects timestamp= (platform-only), so the date goes in the text.
        m.add([{"role": "user", "content": f"{s['title']} ({s['filename']}, recorded {s['recorded_at']}): {sec['text']}"}],
              user_id=USER, metadata=meta)


def delete(sid):
    for r in m.get_all(filters={"user_id": USER, "source": sid}, top_k=1000)["results"]:
        m.delete(r["id"])


def retrieve(q, role, as_of=None):
    # reference_date is platform-only in Mem0, so no date filter here.
    res = m.search(q, top_k=8, filters={"user_id": USER, f"role_{role}": True})["results"]
    return [{"source": (r.get("metadata") or {}).get("source", "?"), "text": r["memory"]} for r in res]


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        fn = {"/ingest": ingest, "/delete": delete, "/retrieve": retrieve}[self.path]
        out = json.dumps(fn(**body) if isinstance(body, dict) and self.path == "/retrieve" else fn(body)).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(out)


HTTPServer(("0.0.0.0", 8890), H).serve_forever()

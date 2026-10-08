"""Mem0 OSS (library on memory-lab via servers/mem0_server.py). Roles as metadata filters, timestamps, delete by source."""
import json, os, urllib.request

URL = os.environ.get("MEM0_URL", "http://memory-lab:8890")


def call(path, body):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.loads(r.read())


def ingest(source): call("/ingest", source)
def delete(source_id): call("/delete", source_id)
def retrieve(question, role, as_of=None): return call("/retrieve", {"q": question, "role": role, "as_of": as_of})

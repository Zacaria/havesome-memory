"""OpenViking (AGPL, self-hosted on memory-lab). Roles as k=v retrieval tags, delete by viking:// path.
OpenViking has no per-document date field, so the recorded date goes in the text."""
import json, os, subprocess, time, urllib.parse, urllib.request, uuid

URL = os.environ.get("OPENVIKING_URL", "http://memory-lab:1933") + "/api/v1"
KEY = os.environ.get("OPENVIKING_KEY") or subprocess.run(
    ["ssh", "memory-lab", "cat ~/ov-key"], capture_output=True, text=True, check=True).stdout.strip()
ROOT = f"viking://resources/morrow-{int(time.time())}"  # fresh folder per run


def call(method, path, body=None, raw=None, ctype="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(URL + path, method=method, data=data, headers={"Content-Type": ctype, "X-API-Key": KEY})
    with urllib.request.urlopen(req, timeout=1800) as r:
        out = json.loads(r.read() or b"null")
    if isinstance(out, dict) and out.get("status") not in (None, "ok"):
        raise RuntimeError(out)
    return out.get("result") if isinstance(out, dict) else out


def upload(name, text):
    b = uuid.uuid4().hex
    raw = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
           f"Content-Type: text/markdown\r\n\r\n{text}\r\n--{b}--\r\n").encode()
    return call("POST", "/resources/temp_upload", raw=raw, ctype=f"multipart/form-data; boundary={b}")["temp_file_id"]


def ingest(source):
    text = f"# {source['title']} ({source['filename']}, recorded {source['recorded_at']})\n\n" + "\n\n".join(s["text"] for s in source["sections"])
    call("POST", "/resources", {"temp_file_id": upload(f"{source['id']}.md", text), "to": f"{ROOT}/{source['id']}.md",
                                "wait": True, "timeout": 1500, "tags": [f"role_{r}=yes" for r in source["roles"]]})


def delete(source_id):
    call("DELETE", "/fs?" + urllib.parse.urlencode({"uri": f"{ROOT}/{source_id}.md", "recursive": "true"}))


def retrieve(question, role, as_of=None):
    # find returns summaries; the documented agent flow then reads the matched files (find -> read).
    res = call("POST", "/search/find", {"query": question, "target_uri": ROOT, "limit": 8, "tags": [f"role_{role}=yes"]})
    sids = []
    for r in (res or {}).get("resources", []):
        sid = r["uri"].removeprefix(ROOT + "/").split("/")[0].split(".")[0]
        if sid.startswith("S") and sid not in sids:
            sids.append(sid)
    return [{"source": s, "text": call("GET", "/content/read?" + urllib.parse.urlencode({"uri": f"{ROOT}/{s}.md/{s}.md"}))} for s in sids]  # "to" path becomes a folder holding the file

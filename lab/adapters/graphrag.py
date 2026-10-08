"""Microsoft GraphRAG 3.2 on memory-lab (~/gr). No roles, no per-document delete: as shipped, removing a document
means deleting its input file and rebuilding the index, which this adapter does lazily before each retrieval."""
import json, shlex, subprocess

dirty = True


def ssh(cmd, inp=None):
    return subprocess.run(["ssh", "memory-lab", cmd], input=inp, capture_output=True, text=True, check=True, timeout=7200).stdout


ssh("rm -rf ~/gr/input/* ~/gr/output ~/gr/cache ~/gr/logs")  # fresh index per run


def ingest(source):
    global dirty
    text = f"# {source['title']} ({source['filename']}, recorded {source['recorded_at']})\n\n" + "\n\n".join(s["text"] for s in source["sections"])
    ssh(f"cat > ~/gr/input/{source['id']}.txt", text); dirty = True


def delete(source_id):
    global dirty
    ssh(f"rm -f ~/gr/input/{source_id}.txt ~/gr/cache -r"); dirty = True  # drop cache too, so nothing derived survives


def retrieve(question, role, as_of=None):  # role ignored: GraphRAG has no access control
    global dirty
    if dirty:
        ssh("cd ~/gr && rm -rf output && ~/graphrag/bin/graphrag index --root . >/dev/null"); dirty = False
    return json.loads(ssh(f"~/graphrag/bin/python ~/graphrag_query.py {shlex.quote(question)} 2>/dev/null").strip().splitlines()[-1])

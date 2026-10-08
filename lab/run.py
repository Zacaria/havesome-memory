#!/usr/bin/env python3
"""Morrow Works scenario test. Usage: run.py <adapter> [--corpus PATH] [--out DIR]

An adapter is a module in adapters/ exposing:
  ingest(source: dict) -> None          # one corpus source (id, filename, sections...)
  delete(source_id: str) -> None        # purge source and everything derived from it
  retrieve(question, role, as_of) -> list[dict]   # [{"source": "S03", "text": "..."}]
Every system gets the same answering step (Codex, same model, same prompt) so only memory differs.
"""
import argparse, importlib.util, json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).parent
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["status", "answer", "citations"],
          "properties": {"status": {"enum": ["answered", "unresolved", "unknown", "refused"]},
                         "answer": {"type": "string"},
                         "citations": {"type": "array", "items": {"type": "string"}}}}
PROMPT = """You answer questions for Morrow Works staff and members. Today is {as_of}. The reader's role is {role}.
Use ONLY the retrieved passages below. Cite source IDs (like S03) you relied on.
status: "answered" if the passages settle it; "unresolved" if they conflict with no rule to pick one;
"unknown" if they don't say; "refused" if the reader may not see the information.

Question: {q}

Retrieved passages:
{passages}"""


def answer(item, passages, model):
    text = "\n".join(f"[{p['source']}] {p['text']}" for p in passages) or "(none)"
    with tempfile.TemporaryDirectory() as tmp:
        schema, out = Path(tmp, "schema.json"), Path(tmp, "out.json")
        schema.write_text(json.dumps(SCHEMA))
        cmd = ["codex", "exec", "--ephemeral", "--skip-git-repo-check", "-s", "read-only", "-C", tmp,
               "--output-schema", str(schema), "-o", str(out)] + (["-m", model] if model else [])
        prompt = PROMPT.format(passages=text, **item)
        subprocess.run(cmd + [prompt], check=True, capture_output=True, text=True, timeout=300)
        return json.loads(out.read_text())


def score(expect, result, passages):
    """Plain string checks; returns list of failed rule names (empty = pass)."""
    a, cites = result["answer"].lower(), set(result["citations"])
    seen = " ".join(p["source"] + " " + p["text"] for p in passages).lower()
    fails = []
    if "status" in expect and result["status"] != expect["status"]: fails.append("status")
    if expect.get("value_any") and not any(v.lower() in a for v in expect["value_any"]): fails.append("value_any")
    if any(v.lower() in a for v in expect.get("value_none", [])): fails.append("value_none")
    if not set(expect.get("cite_all", [])) <= cites: fails.append("cite_all")
    if cites & set(expect.get("cite_none", [])): fails.append("cite_none")
    if any(v.lower() in seen for v in expect.get("passages_none", [])): fails.append("passages_none")
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("adapter"); ap.add_argument("--model", default="")
    ap.add_argument("--corpus", default=str(HERE / "corpus.json"))
    ap.add_argument("--out", default=str(HERE / "results"))
    args = ap.parse_args()
    # Load by path, not sys.path: adapter names may shadow stdlib modules (e.g. "keyword").
    spec = importlib.util.spec_from_file_location(f"adapter_{args.adapter}", HERE / "adapters" / f"{args.adapter}.py")
    mem = importlib.util.module_from_spec(spec); spec.loader.exec_module(mem)
    sources = sorted(json.loads(Path(args.corpus).read_text())["sources"], key=lambda s: s["ingested_at"])
    plan = json.loads((HERE / "questions.json").read_text())
    done, deleted, rows = set(), set(), []
    for item in sorted(plan["questions"], key=lambda q: q["as_of"]):
        for s in sources:  # replay the timeline up to this question's date
            if s["id"] not in done and s["ingested_at"] <= item["as_of"]:
                mem.ingest(s); done.add(s["id"])
        for d in plan["deletions"]:
            if d["source"] not in deleted and d["at"] <= item["as_of"]:
                mem.delete(d["source"]); deleted.add(d["source"])
        passages = mem.retrieve(item["q"], item["role"], as_of=item["as_of"])
        result = answer(item, passages, args.model)
        fails = score(item["expect"], result, passages)
        rows.append({"id": item["id"], "pass": not fails, "fails": fails, "result": result, "passages": passages})
        print(f"{item['id']:24} {'PASS' if not fails else 'FAIL ' + ','.join(fails)}", flush=True)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    Path(args.out, f"{args.adapter}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(f"{args.adapter}: {sum(r['pass'] for r in rows)}/{len(rows)}")


if __name__ == "__main__":
    main()

"""Run on memory-lab: GraphRAG local search over ~/gr, print the source text units it retrieved as JSON.
GraphRAG has no roles or per-document delete: the adapter rebuilds the index from the current input files."""
import asyncio, json, sys
from pathlib import Path
import pandas as pd
import graphrag.api as api
from graphrag.config.load_config import load_config

ROOT = Path("/home/lab/gr")
t = lambda n: pd.read_parquet(ROOT / "output" / f"{n}.parquet")
tus, docs = t("text_units"), t("documents")
_, ctx = asyncio.run(api.local_search(
    config=load_config(ROOT), entities=t("entities"), communities=t("communities"),
    community_reports=t("community_reports"), text_units=tus, relationships=t("relationships"),
    covariates=None, community_level=2, response_type="Multiple Paragraphs", query=sys.argv[1]))
doc_of = dict(zip(tus["text"], tus["document_id"] if "document_id" in tus else tus["document_ids"].str[0]))
title = dict(zip(docs["id"], docs["title"]))
print(json.dumps([{"source": Path(title.get(doc_of.get(txt), "?")).stem, "text": txt} for txt in ctx["sources"]["text"]]))

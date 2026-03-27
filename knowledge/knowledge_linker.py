"""knowledge/knowledge_linker.py — Attaches relevant memory to live objects."""
from __future__ import annotations
from typing import Any
from knowledge.context_retrieval_engine import retrieve_relevant_knowledge

def attach_knowledge_context(row: dict[str,Any], knowledge_entries: list[dict[str,Any]],
                              environment: str) -> dict[str,Any]:
    relevant=retrieve_relevant_knowledge(knowledge_entries,environment,
                                          symbol=row.get("symbol"),
                                          playbook_code=row.get("playbook_code"),max_results=5)
    out=dict(row)
    out["knowledge_context"]=relevant
    out["knowledge_context_summaries"]=[k.get("summary","") for k in relevant]
    return out

"""knowledge/context_retrieval_engine.py — Fetches relevant memory by symbol/playbook/tags."""
from __future__ import annotations
from typing import Any

def retrieve_relevant_knowledge(knowledge_entries: list[dict[str,Any]], environment: str,
                                 symbol: str|None=None, playbook_code: str|None=None,
                                 tags: list[str]|None=None, max_results: int=10) -> list[dict[str,Any]]:
    tags=tags or []; results=[]
    for e in knowledge_entries:
        if e.get("environment")!=environment or e.get("status")!="ACTIVE": continue
        hit=(symbol        and e.get("subject_type")=="SYMBOL"   and e.get("subject_id")==symbol) or \
            (playbook_code and e.get("subject_type")=="PLAYBOOK" and e.get("subject_id")==playbook_code) or \
            (tags          and any(t in e.get("tags",[]) for t in tags))
        if hit: results.append(e)
    return results[:max_results]

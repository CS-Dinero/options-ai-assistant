"""knowledge/policy_rationale_memory.py — Stores why policy changes were made."""
from __future__ import annotations
from typing import Any
from knowledge.knowledge_entry_builder import build_knowledge_entry

def build_policy_rationale_entry(environment: str, policy_version_id: str, summary: str,
                                  rationale_details: dict[str,Any], source_object_ids: list[str],
                                  active_mandate: str|None=None) -> dict[str,Any]:
    details = dict(rationale_details)
    if active_mandate: details["active_mandate"] = active_mandate
    return build_knowledge_entry(environment,"POLICY_RATIONALE","CONTROL_PLANE",
                                  source_object_ids,"POLICY_VERSION",policy_version_id,
                                  summary,details,["POLICY","RATIONALE"],"HIGH")

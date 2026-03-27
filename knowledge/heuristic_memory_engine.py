"""knowledge/heuristic_memory_engine.py — Stores approved operating heuristics."""
from __future__ import annotations
from typing import Any
from knowledge.knowledge_entry_builder import build_knowledge_entry

def build_heuristic_entry(environment: str, subject_type: str, subject_id: str,
                            summary: str, evidence: dict[str,Any],
                            source_object_ids: list[str]) -> dict[str,Any]:
    return build_knowledge_entry(environment,"APPROVED_HEURISTIC","HEURISTIC_ENGINE",
                                  source_object_ids,subject_type,subject_id,
                                  summary,evidence,["HEURISTIC"],"MEDIUM")

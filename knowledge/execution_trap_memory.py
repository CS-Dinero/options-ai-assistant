"""knowledge/execution_trap_memory.py — Stores repeatable execution failure patterns."""
from __future__ import annotations
from typing import Any
from knowledge.knowledge_entry_builder import build_knowledge_entry

def build_execution_trap_entry(environment: str, symbol: str, summary: str,
                                trap_details: dict[str,Any], source_object_ids: list[str]) -> dict[str,Any]:
    return build_knowledge_entry(environment,"EXECUTION_TRAP","EXECUTION_ANALYSIS",
                                  source_object_ids,"SYMBOL",symbol,
                                  summary,trap_details,["EXECUTION","TRAP"],"MEDIUM")
